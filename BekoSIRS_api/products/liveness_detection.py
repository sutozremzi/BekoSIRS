"""
products/liveness_detection.py
==============================
Active Liveness Detection — Frame Subtraction + Head Pose (Yaw) Estimation
---------------------------------------------------------------------------

İş akışı:
  1. Kullanıcıdan kameraya kısa bir video akışı sırasında 3 key-frame alınır:
       Sol  (yaw ≈ -30°)  →  frame_left
       Merkez (yaw ≈  0°)  →  frame_center
       Sağ  (yaw ≈ +30°)  →  frame_right

  2. Yüz landmarkları üzerinden Yaw açısı hesaplanır (MediaPipe FaceMesh ya da
     OpenCV solvePnP fallback).  Belirlenen eşiklere ulaşınca frame otomatik
     kaydedilir (bu iş frontend'de yapılır; backend sadece gelen 3 frame'i analiz eder).

  3. Frame Subtraction:
       diff_L_C  = |frame_left  − frame_center|   (gri tonlama)
       diff_C_R  = |frame_center − frame_right|
       diff_L_R  = |frame_left  − frame_right|

  4. Analiz:
     • Gerçek insan: 3D perspektif + arka plan paralaks → büyük, dağılmış fark piksel alanları
     • Sahte (fotoğraf/ekran): düz yüzey → küçük, düzgün fark alanları
     Liveness score = ortanca (diff_L_C, diff_C_R, diff_L_R) normalise değeri üretilir.
     Eşiğin üzerindeyse → CANLI.

Bağımlılıklar (pip):
  opencv-python
  numpy
  mediapipe           (isteğe bağlı; yoksa solvePnP fallback devreye girer)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler & eşikler
# ---------------------------------------------------------------------------

# Güvenilir liveness skoru için minimum piksel fark ortalaması (0-255)
LIVENESS_SCORE_THRESHOLD = 15.0

# Yüz algılanamadığında veya sadece 2 frame geldiğinde kullanılacak alt eşik
MIN_DIFF_PAIRWISE = 5.0

# Sahte saldırı için fark haritasının entropisi (Shannon) alt sınırı
ENTROPY_THRESHOLD = 4.2

# Asgari "aktif piksel" oranı (fark haritasında 15'ten büyük piksel / toplam piksel)
ACTIVE_PIXEL_RATIO_MIN = 0.08

# Yaw açısı hedefleri (derece) — her frame'in doğru açıda olduğu kontrol edilir
YAW_LEFT_TARGET   = -25.0
YAW_CENTER_TARGET =   0.0
YAW_RIGHT_TARGET  =  25.0
YAW_TOLERANCE     =  15.0   # ±15° kabul aralığı

# Yön doğrulamak için minimum yaw sapma eşiği
# Sol frame'in yaw'u bu değerden küçük, sağ frame'in bu değerden büyük olmalı
YAW_MIN_SIDE_ANGLE = 10.0   # En az ±10° dönmüş olmalı


# ---------------------------------------------------------------------------
# Yardımcı: Görüntüyü gri+blur ile normalize et
# ---------------------------------------------------------------------------

def _preprocess(img: np.ndarray, size: tuple[int, int] = (320, 240)) -> np.ndarray:
    """BGR → Gri, yeniden boyutlandır, Gaussian blur (gürültüyü bastırır)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(resized, (5, 5), 0)
    return blurred


# ---------------------------------------------------------------------------
# Yardımcı: Shannon entropisi (fark haritası üzerinde)
# ---------------------------------------------------------------------------

def _entropy(hist_vals: np.ndarray) -> float:
    """1D histogram değerlerinden Shannon entropisi hesapla."""
    total = hist_vals.sum()
    if total == 0:
        return 0.0
    probs = hist_vals[hist_vals > 0] / total
    return float(-np.sum(probs * np.log2(probs)))


# ---------------------------------------------------------------------------
# Temel analiz fonksiyonu: 2 frame arasındaki fark metrikleri
# ---------------------------------------------------------------------------

@dataclass
class PairDiffResult:
    mean_diff: float        # Ortalama piksel farkı  (0-255)
    active_ratio: float     # Eşik üstü piksel oranı (0-1)
    entropy: float          # Fark haritasının Shannon entropisi
    diff_map: np.ndarray = field(default=None, repr=False)  # Görselleştirme için


def _pair_diff(a: np.ndarray, b: np.ndarray, threshold: int = 15) -> PairDiffResult:
    """
    İki gri görüntü arasındaki piksel fark metriklerini hesapla.

    Args:
        a, b   : Gri ve normalize edilmiş görüntüler (aynı boyut).
        threshold: Aktif piksel sayımı için fark eşiği.
    """
    diff = cv2.absdiff(a, b).astype(np.float32)
    mean_diff = float(diff.mean())

    active_pixels = int((diff > threshold).sum())
    total_pixels = diff.size
    active_ratio = active_pixels / total_pixels if total_pixels > 0 else 0.0

    # 256 bin histogram → entropi
    hist, _ = np.histogram(diff.astype(np.uint8), bins=256, range=(0, 255))
    entropy = _entropy(hist)

    return PairDiffResult(
        mean_diff=mean_diff,
        active_ratio=active_ratio,
        entropy=entropy,
        diff_map=diff.astype(np.uint8),
    )


# ---------------------------------------------------------------------------
# Ana liveness skor hesaplayıcı
# ---------------------------------------------------------------------------

@dataclass
class LivenessResult:
    is_live: bool
    score: float                  # 0-1 arası normalise skor (1 = kesinlikle canlı)
    reason: str                   # İnsan okunabilir açıklama
    details: dict = field(default_factory=dict)


def compute_liveness_score(
    frame_left: np.ndarray,
    frame_center: np.ndarray,
    frame_right: np.ndarray,
    score_threshold: float = LIVENESS_SCORE_THRESHOLD,
    verify_pose: bool = True,
) -> LivenessResult:
    """
    3 frame arasındaki frame subtraction metriklerinden liveness skoru üret.

    Args:
        frame_left   : Sol açıdaki BGR frame (yaw ≈ -25°).
        frame_center : Merkez BGR frame     (yaw ≈ 0°).
        frame_right  : Sağ açıdaki BGR frame (yaw ≈ +25°).
        score_threshold: Bu değerin altındaki ortalama fark sahte kabul edilir.
        verify_pose  : True ise HeadPoseEstimator ile yön doğrulanması yapılır.

    Returns:
        LivenessResult
    """

    fail_reasons = []

    # ------------------------------------------------------------------ #
    # 1. Yön doğrulaması — Yüz Aspect Ratio ile bakış yönü tespiti
    #
    # Mantık: Yüz öne bakarken en geniştir (yüksek aspect ratio = geniş/boy).
    # Sola veya sağa döndükçe yüzün görünen genişliği AZALIR.
    # Bu yüzden: merkez frame AR > sol frame AR VE merkez frame AR > sağ frame AR
    #
    # Haar frontal cascade yan yüzleri algılayamaz, bu yüzden:
    # - Merkez frame: Haar ile yüz bul (öne bakıyor, kolayca bulunur)
    # - Sol/Sağ frame: Haar bulamazsa AR=0 kabul et (yeterince döndü demek)
    # ------------------------------------------------------------------ #
    if verify_pose:
        _haar = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        def _face_aspect_ratio(img_bgr):
            """En büyük yüzün genişlik/yükseklik oranını döndür. Yüz yoksa 0.0."""
            gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            faces = _haar.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50)
            )
            if len(faces) == 0:
                return 0.0
            x, y, fw, fh = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
            return fw / fh if fh > 0 else 0.0

        ar_left   = _face_aspect_ratio(frame_left)
        ar_center = _face_aspect_ratio(frame_center)
        ar_right  = _face_aspect_ratio(frame_right)

        logger.info(
            "Face aspect ratio → left=%.3f, center=%.3f, right=%.3f",
            ar_left, ar_center, ar_right,
        )

        # Merkez frame'de kesinlikle yüz bulunabilmeli
        if ar_center < 0.3:
            fail_reasons.append(
                "Merkez frame'de yüz tespit edilemedi. "
                "Lütfen orta adımda kameraya düz bakın."
            )
        else:
            # Merkez, sol ve sağdan daha geniş olmalı
            # (sola/sağa dönünce Haar bulamazsa ar=0 → zaten merkez kazanır)
            MARGIN = 0.04  # En az %4 daha geniş olmalı — çok küçük hareket geçmesin

            if ar_center < ar_left + MARGIN and ar_left > 0.1:
                fail_reasons.append(
                    f"Merkez frame sol frame'den daha geniş değil "
                    f"(merkez AR={ar_center:.3f}, sol AR={ar_left:.3f}). "
                    f"Sol adımda başınızı daha belirgin çevirin, "
                    f"merkez adımda düz öne bakın."
                )
            if ar_center < ar_right + MARGIN and ar_right > 0.1:
                fail_reasons.append(
                    f"Merkez frame sağ frame'den daha geniş değil "
                    f"(merkez AR={ar_center:.3f}, sağ AR={ar_right:.3f}). "
                    f"Sağ adımda başınızı daha belirgin çevirin, "
                    f"merkez adımda düz öne bakın."
                )

    # Eğer yön hataları varsa hemen dön
    if fail_reasons:
        return LivenessResult(
            is_live=False,
            score=0.0,
            reason="Canlılık doğrulaması başarısız: " + "; ".join(fail_reasons),
            details={},
        )

    # ------------------------------------------------------------------ #
    # 2. Ön işleme
    # ------------------------------------------------------------------ #
    p_left   = _preprocess(frame_left)
    p_center = _preprocess(frame_center)
    p_right  = _preprocess(frame_right)

    # ------------------------------------------------------------------ #
    # 3. 3 çift için fark metrikleri
    # ------------------------------------------------------------------ #
    r_lc = _pair_diff(p_left,   p_center)   # Sol  ↔ Merkez
    r_cr = _pair_diff(p_center, p_right)    # Merkez ↔ Sağ
    r_lr = _pair_diff(p_left,   p_right)    # Sol  ↔ Sağ  (en büyük açı farkı)

    # ------------------------------------------------------------------ #
    # 4. Kombine metrikler (ağırlıklı ortalama — L↔R daha kritik)
    # ------------------------------------------------------------------ #
    weights = np.array([1.0, 1.0, 1.5])
    mean_diffs    = np.array([r_lc.mean_diff,    r_cr.mean_diff,    r_lr.mean_diff])
    active_ratios = np.array([r_lc.active_ratio, r_cr.active_ratio, r_lr.active_ratio])
    entropies     = np.array([r_lc.entropy,      r_cr.entropy,      r_lr.entropy])

    weighted_mean_diff    = float(np.average(mean_diffs,    weights=weights))
    weighted_active_ratio = float(np.average(active_ratios, weights=weights))
    weighted_entropy      = float(np.average(entropies,     weights=weights))

    # ------------------------------------------------------------------ #
    # 5. Normalise liveness skoru (0-1)
    # ------------------------------------------------------------------ #
    norm_diff    = min(weighted_mean_diff / 50.0, 1.0)
    norm_active  = min(weighted_active_ratio / 0.20, 1.0)
    norm_entropy = min(weighted_entropy / 6.0, 1.0)

    score = float((norm_diff * norm_active * norm_entropy) ** (1 / 3))

    # ------------------------------------------------------------------ #
    # 6. Eşik kontrolleri
    # ------------------------------------------------------------------ #
    if weighted_mean_diff < score_threshold:
        fail_reasons.append(
            f"Ortalama piksel farkı çok düşük ({weighted_mean_diff:.2f} < {score_threshold}) — "
            f"daha belirgin bir baş hareketi yapın."
        )

    if weighted_active_ratio < ACTIVE_PIXEL_RATIO_MIN:
        fail_reasons.append(
            f"Aktif piksel oranı çok düşük ({weighted_active_ratio*100:.1f}% < {ACTIVE_PIXEL_RATIO_MIN*100:.0f}%)."
        )

    if weighted_entropy < ENTROPY_THRESHOLD:
        fail_reasons.append(
            f"Fark haritası entropisi çok düşük ({weighted_entropy:.2f} < {ENTROPY_THRESHOLD}) — "
            f"fotoğraf veya ekran saldırısı şüphesi."
        )

    is_live = len(fail_reasons) == 0

    if is_live:
        reason = (
            f"Canlılık doğrulandı. "
            f"Ortalama Δpiksel={weighted_mean_diff:.2f}, "
            f"Aktif piksel=%{weighted_active_ratio*100:.1f}, "
            f"Entropi={weighted_entropy:.2f}"
        )
    else:
        reason = "Canlılık doğrulaması başarısız: " + "; ".join(fail_reasons)

    logger.info(
        "LivenessScore → score=%.3f, mean_diff=%.2f, active=%.2f%%, entropy=%.2f, is_live=%s",
        score, weighted_mean_diff, weighted_active_ratio * 100, weighted_entropy, is_live,
    )

    return LivenessResult(
        is_live=is_live,
        score=round(score, 4),
        reason=reason,
        details={
            "pairs": {
                "left_center":  {"mean_diff": round(r_lc.mean_diff, 2), "active_ratio": round(r_lc.active_ratio, 4), "entropy": round(r_lc.entropy, 3)},
                "center_right": {"mean_diff": round(r_cr.mean_diff, 2), "active_ratio": round(r_cr.active_ratio, 4), "entropy": round(r_cr.entropy, 3)},
                "left_right":   {"mean_diff": round(r_lr.mean_diff, 2), "active_ratio": round(r_lr.active_ratio, 4), "entropy": round(r_lr.entropy, 3)},
            },
            "combined": {
                "weighted_mean_diff":    round(weighted_mean_diff, 2),
                "weighted_active_ratio": round(weighted_active_ratio, 4),
                "weighted_entropy":      round(weighted_entropy, 3),
            },
            "thresholds": {
                "score_threshold":        score_threshold,
                "active_pixel_ratio_min": ACTIVE_PIXEL_RATIO_MIN,
                "entropy_threshold":      ENTROPY_THRESHOLD,
            },
        },
    )


# ---------------------------------------------------------------------------
# Head Pose (Yaw) Tahmincisi  — MediaPipe veya solvePnP fallback
# ---------------------------------------------------------------------------

class HeadPoseEstimator:
    """
    Tek bir BGR frame'den Yaw açısını (derece) tahmin eder.

    Önce MediaPipe FaceMesh dener; kurulu değilse
    OpenCV Haar Cascade + solvePnP ile yaklaşık açı hesaplar.
    """

    def __init__(self):
        self._mp_available = False
        self._face_mesh    = None
        self._haar_cascade = None

        # MediaPipe dene
        try:
            import mediapipe as mp
            self._mp = mp
            self._mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = self._mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )
            self._mp_available = True
            logger.info("HeadPoseEstimator: MediaPipe FaceMesh kullanılıyor.")
        except ImportError:
            logger.warning("HeadPoseEstimator: MediaPipe bulunamadı → solvePnP fallback.")
            self._haar_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

    def estimate_yaw(self, frame_bgr: np.ndarray) -> Optional[float]:
        """
        Verilen BGR frame'den Yaw açısını derece olarak döndür.
        Yüz bulunamazsa None döner.
        """
        if self._mp_available:
            return self._yaw_mediapipe(frame_bgr)
        else:
            return self._yaw_solvepnp(frame_bgr)

    # --- MediaPipe yolu ---
    def _yaw_mediapipe(self, frame_bgr: np.ndarray) -> Optional[float]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark
        h, w = frame_bgr.shape[:2]

        # 3D referans model (cm cinsinden) — MediaPipe kanonік yüz modeli
        # Landmark indisleri: Burun ucu=1, Çene=152, Sol göz dış=33, Sağ göz dış=263, Sol ağız=61, Sağ ağız=291
        model_3d = np.array([
            [  0.0,   0.0,   0.0],    # 1  - Burun ucu
            [  0.0, -330.0, -65.0],   # 152 - Çene
            [-225.0, 170.0, -135.0],  # 33  - Sol göz dış köşe
            [ 225.0, 170.0, -135.0],  # 263 - Sağ göz dış köşe
            [-150.0,-150.0, -125.0],  # 61  - Sol ağız köşe
            [ 150.0,-150.0, -125.0],  # 291 - Sağ ağız köşe
        ], dtype=np.float64)

        indices = [1, 152, 33, 263, 61, 291]
        img_2d = np.array([
            [landmarks[i].x * w, landmarks[i].y * h] for i in indices
        ], dtype=np.float64)

        focal = w
        cam_matrix = np.array([
            [focal,     0, w / 2],
            [0,     focal, h / 2],
            [0,         0,     1],
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))

        success, rot_vec, _ = cv2.solvePnP(
            model_3d, img_2d, cam_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return None

        rot_mat, _ = cv2.Rodrigues(rot_vec)
        # Euler açılarına dönüştür
        sy = math.sqrt(rot_mat[0, 0] ** 2 + rot_mat[1, 0] ** 2)
        singular = sy < 1e-6
        if not singular:
            yaw = math.atan2(rot_mat[1, 0], rot_mat[0, 0])
        else:
            yaw = math.atan2(-rot_mat[1, 2], rot_mat[1, 1])

        return math.degrees(yaw)

    # --- solvePnP fallback (Haar yüz tespiti ile basit yatay offset tahmini) ---
    def _yaw_solvepnp(self, frame_bgr: np.ndarray) -> Optional[float]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._haar_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        if len(faces) == 0:
            return None

        x, y, fw, fh = faces[0]
        face_center_x = x + fw / 2
        frame_center_x = frame_bgr.shape[1] / 2

        # Basit tahmin: yüz merkezinin frame merkezinden sapması ≈ yaw
        offset_ratio = (face_center_x - frame_center_x) / (frame_bgr.shape[1] / 2)
        estimated_yaw = offset_ratio * 45.0   # ±45° maks
        return estimated_yaw

    def close(self):
        if self._face_mesh:
            self._face_mesh.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# Yüksek seviyeli yardımcı: byte dizisinden numpy'a dönüştür
# ---------------------------------------------------------------------------

def decode_image_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """
    Gelen raw byte akışını (JPEG/PNG vb.) OpenCV BGR numpy dizisine çevir.
    Hata durumunda None döner.
    """
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error("decode_image_bytes hatası: %s", e)
        return None


# ---------------------------------------------------------------------------
# Kolaylık fonksiyonu: Tek seferlik analiz (görünüm katmanı için)
# ---------------------------------------------------------------------------

def run_liveness_check(
    left_bytes: bytes,
    center_bytes: bytes,
    right_bytes: bytes,
    score_threshold: float = LIVENESS_SCORE_THRESHOLD,
) -> LivenessResult:
    """
    3 frame'in byte dizisini alır, decode eder ve liveness skoru döndürür.
    Görünüm katmanından (biometric_views.py) doğrudan çağrılır.

    Args:
        left_bytes   : Sol  açı görüntüsünün ham byte içeriği.
        center_bytes : Merkez görüntünün ham byte içeriği.
        right_bytes  : Sağ  açı görüntüsünün ham byte içeriği.
        score_threshold : Canlılık skoru için alt sınır.

    Returns:
        LivenessResult
    """
    frames = {}
    for name, raw in [("left", left_bytes), ("center", center_bytes), ("right", right_bytes)]:
        img = decode_image_bytes(raw)
        if img is None:
            return LivenessResult(
                is_live=False,
                score=0.0,
                reason=f"'{name}' frame decode edilemedi. Geçerli bir görüntü dosyası gönderin.",
            )
        frames[name] = img

    return compute_liveness_score(
        frame_left=frames["left"],
        frame_center=frames["center"],
        frame_right=frames["right"],
        score_threshold=score_threshold,
    )


# ---------------------------------------------------------------------------
# Multi-Frame Liveness Detection — Video yerine JPEG dizisi (Ana yöntem)
# ---------------------------------------------------------------------------

def run_liveness_check_multiframe(
    frame_bytes_list: list[bytes],
    min_motion_score: float = 5.0,
    min_entropy: float = 3.5,
) -> LivenessResult:
    """
    Ardışık JPEG frame listesinden liveness skoru üretir.

    Video codec sorununu ortadan kaldırır: frontend N tane JPEG gönderir
    (örn. her 500ms'de bir çekilen fotoğraf), backend ardışık çiftler
    arasındaki frame subtraction metriklerini hesaplar.

    Gerçek insan: baş hareketi → yüksek piksel farkı + yüksek entropi
    Sahte (foto/ekran): statik → düşük piksel farkı + düşük entropi

    Args:
        frame_bytes_list : En az 4, en fazla 20 JPEG byte listesi.
        min_motion_score : Ortalama piksel farkı alt eşiği.
        min_entropy      : Entropi alt eşiği.

    Returns:
        LivenessResult
    """
    if len(frame_bytes_list) < 3:
        return LivenessResult(
            is_live=False, score=0.0,
            reason=f"Yetersiz frame ({len(frame_bytes_list)}). En az 3 frame gönderilmeli.",
        )

    # Frame'leri decode et
    decoded = []
    for i, raw in enumerate(frame_bytes_list):
        img = decode_image_bytes(raw)
        if img is None:
            logger.warning("Frame %d decode edilemedi, atlanıyor.", i)
            continue
        decoded.append(_preprocess(img))

    if len(decoded) < 3:
        return LivenessResult(
            is_live=False, score=0.0,
            reason="Yeterli sayıda frame decode edilemedi. Lütfen tekrar deneyin.",
        )

    # Ardışık frame çiftleri arasındaki fark metrikleri
    pair_results = [
        _pair_diff(decoded[i], decoded[i + 1])
        for i in range(len(decoded) - 1)
    ]

    mean_diffs    = np.array([r.mean_diff    for r in pair_results])
    active_ratios = np.array([r.active_ratio for r in pair_results])
    entropies     = np.array([r.entropy      for r in pair_results])

    # Medyan (uç değerlere dayanıklı — bir frame kötü gelse bile patlamaz)
    median_diff    = float(np.median(mean_diffs))
    median_active  = float(np.median(active_ratios))
    median_entropy = float(np.median(entropies))

    logger.info(
        "MultiFrameLiveness → frames=%d, median_diff=%.2f, active=%.1f%%, entropy=%.2f",
        len(decoded), median_diff, median_active * 100, median_entropy,
    )

    # Normalise skor (0-1)
    norm_diff    = min(median_diff    / 35.0, 1.0)   # 35+ piksel farkı = tam puan
    norm_active  = min(median_active  / 0.15, 1.0)   # %15+ = tam puan
    norm_entropy = min(median_entropy / 6.0,  1.0)   # 6 bit = tam puan
    score = float((norm_diff * norm_active * norm_entropy) ** (1 / 3))

    # Karar
    fail_reasons = []
    if median_diff < min_motion_score:
        fail_reasons.append(
            f"Hareket yeterli değil (Δpiksel={median_diff:.2f} < {min_motion_score}). "
            f"Başınızı daha belirgin şekilde hareket ettirin."
        )
    if median_entropy < min_entropy:
        fail_reasons.append(
            f"Hareket entropisi düşük ({median_entropy:.2f} < {min_entropy}) — "
            f"fotoğraf/ekran saldırısı şüphesi."
        )

    is_live = len(fail_reasons) == 0
    reason = (
        f"Canlılık doğrulandı — Δpiksel={median_diff:.2f}, "
        f"aktif=%{median_active*100:.1f}, entropi={median_entropy:.2f}"
        if is_live
        else "Canlılık doğrulaması başarısız: " + "; ".join(fail_reasons)
    )

    return LivenessResult(
        is_live=is_live,
        score=round(score, 4),
        reason=reason,
        details={
            "frames_analyzed": len(decoded),
            "median_diff":    round(median_diff,    2),
            "median_active":  round(median_active,  4),
            "median_entropy": round(median_entropy, 3),
            "thresholds": {
                "min_motion_score": min_motion_score,
                "min_entropy":      min_entropy,
            },
        },
    )


# ---------------------------------------------------------------------------
# Video Tabanlı Liveness Detection (Ana yöntem)
# ---------------------------------------------------------------------------

def run_liveness_check_from_video(
    video_bytes: bytes,
    n_frames: int = 12,
    min_motion_score: float = 6.0,
    min_entropy: float = 3.8,
) -> LivenessResult:
    """
    Kısa bir video kaydından (2-4 sn) liveness skoru üretir.

    İş akışı:
      1. Video byte'larını geçici dosyaya yaz
      2. OpenCV VideoCapture ile eşit aralıklı N frame çıkar
      3. Ardışık frame çiftleri arasındaki fark metriklerini hesapla
      4. Ortanca hareket skoru + entropi ile liveness kararı ver

    Gerçek insan: sürekli ve kaotik hareket → yüksek motion + yüksek entropi
    Sahte (fotoğraf/ekran): minimum veya düzenli hareket → düşük motion + düşük entropi

    Args:
        video_bytes     : Video dosyasının ham byte içeriği (mp4, mov vb.)
        n_frames        : Videodan çıkarılacak frame sayısı
        min_motion_score: Ortalama piksel farkı için alt eşik (0-255)
        min_entropy     : Kümülatif entropi için alt eşik

    Returns:
        LivenessResult
    """
    import tempfile
    import os

    # 1. Geçici dosyaya yaz
    suffix = ".mp4"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        # 2. OpenCV ile aç
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return LivenessResult(
                is_live=False, score=0.0,
                reason="Video açılamadı. Desteklenen format: mp4, mov.",
            )

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < 4:
            cap.release()
            return LivenessResult(
                is_live=False, score=0.0,
                reason=f"Video çok kısa ({total_frames} frame). En az 2 saniyelik video gönderin.",
            )

        # 3. Eşit aralıklı frame indisleri
        indices = [int(i * (total_frames - 1) / (n_frames - 1)) for i in range(n_frames)]
        extracted = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                extracted.append(_preprocess(frame))
        cap.release()

        if len(extracted) < 4:
            return LivenessResult(
                is_live=False, score=0.0,
                reason="Videodan yeterli frame çıkarılamadı. Daha iyi aydınlatılmış bir ortamda deneyin.",
            )

        # 4. Ardışık frame çiftleri arasındaki fark metrikleri
        pair_results = [
            _pair_diff(extracted[i], extracted[i + 1])
            for i in range(len(extracted) - 1)
        ]

        mean_diffs    = np.array([r.mean_diff    for r in pair_results])
        active_ratios = np.array([r.active_ratio for r in pair_results])
        entropies     = np.array([r.entropy      for r in pair_results])

        # Medyan kullan (uç değerlere daha dayanıklı)
        median_diff    = float(np.median(mean_diffs))
        median_active  = float(np.median(active_ratios))
        median_entropy = float(np.median(entropies))

        logger.info(
            "VideoLiveness → frames=%d, median_diff=%.2f, median_active=%.2f%%, median_entropy=%.2f",
            len(extracted), median_diff, median_active * 100, median_entropy,
        )

        # 5. Normalise skor
        norm_diff    = min(median_diff    / 40.0, 1.0)
        norm_active  = min(median_active  / 0.15, 1.0)
        norm_entropy = min(median_entropy / 6.0,  1.0)
        score = float((norm_diff * norm_active * norm_entropy) ** (1 / 3))

        # 6. Karar
        fail_reasons = []
        if median_diff < min_motion_score:
            fail_reasons.append(
                f"Hareket yeterli değil (ort. Δpiksel={median_diff:.2f} < {min_motion_score}). "
                f"Lütfen başınızı belirgin şekilde çevirin."
            )
        if median_entropy < min_entropy:
            fail_reasons.append(
                f"Hareket düzensizliği düşük (entropi={median_entropy:.2f} < {min_entropy}) — "
                f"fotoğraf veya ekran saldırısı şüphesi."
            )

        is_live = len(fail_reasons) == 0
        if is_live:
            reason = (
                f"Canlılık doğrulandı. "
                f"Ort. Δpiksel={median_diff:.2f}, "
                f"Aktif piksel=%{median_active*100:.1f}, "
                f"Entropi={median_entropy:.2f}"
            )
        else:
            reason = "Canlılık doğrulaması başarısız: " + "; ".join(fail_reasons)

        return LivenessResult(
            is_live=is_live,
            score=round(score, 4),
            reason=reason,
            details={
                "video_frames_analyzed": len(extracted),
                "median_diff":    round(median_diff,    2),
                "median_active":  round(median_active,  4),
                "median_entropy": round(median_entropy, 3),
                "thresholds": {
                    "min_motion_score": min_motion_score,
                    "min_entropy":      min_entropy,
                },
            },
        )

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
