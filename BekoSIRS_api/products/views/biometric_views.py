# products/views/biometric_views.py
"""
Biometric authentication views (Face ID via DeepFace).

Endpoints:
  • /biometric/enable/              → Yüz kaydı (embedding şifreli saklanır)
  • /biometric/login/               → Tek fotoğraf ile Face ID girişi
  • /biometric/login-with-liveness/ → Liveness + yüz doğrulama (atomik)
  • /biometric/liveness-check/      → 3 frame ile bağımsız liveness kontrolü
  • /biometric/liveness-check-multi/→ N frame ile bağımsız liveness kontrolü
  • /biometric/liveness-check-video/→ Video tabanlı liveness kontrolü
"""

import logging
from django.core.cache import cache

import cv2
import numpy as np
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from products.models import CustomUser
from products.serializers import BiometricEnableSerializer, BiometricLoginSerializer
from products.encryption import encrypt_face_encoding, decrypt_face_encoding
from products.liveness_detection import (
    run_liveness_check,
    run_liveness_check_from_video,
    run_liveness_check_multiframe,
    LivenessResult,
)

logger = logging.getLogger(__name__)

import time

def _get_lockout_remaining(username):
    """
    Returns remaining lockout time in seconds, or 0 if not locked out.
    """
    lockout_expires = cache.get(f"bio_lockout_{username}")
    if lockout_expires:
        now = time.time()
        remaining = int(lockout_expires - now)
        if remaining > 0:
            return remaining
        else:
            cache.delete(f"bio_lockout_{username}")
    return 0

def _handle_biometric_failure(user):
    """
    Increments consecutive failed biometric attempts.
    If it reaches 5, locks out biometric login for 5 minutes.
    Returns (attempts_left, locked_out, lockout_duration_sec)
    """
    username = user.username
    cache_key = f"failed_bio_attempts_{username}"
    attempts = cache.get(cache_key, 0) + 1
    cache.set(cache_key, attempts, timeout=86400)
    
    if attempts >= 5:
        # Lockout for 5 minutes (300 seconds)
        lockout_duration = 300
        expires_at = time.time() + lockout_duration
        cache.set(f"bio_lockout_{username}", expires_at, timeout=lockout_duration)
        cache.delete(cache_key)
        return 0, True, lockout_duration
    
    return 5 - attempts, False, 0

def _reset_biometric_failures(username):
    """Resets the failure counter and lockout on successful login."""
    cache.delete(f"failed_bio_attempts_{username}")
    cache.delete(f"bio_lockout_{username}")

def _format_biometric_error(tr_header, tr_bullets, en_header, en_bullets, left_attempts=None):
    """
    Formats a clean, bilingual error message with bullet points.
    All Turkish content is presented first, followed by all English content.
    """
    tr_lines = [tr_header]
    if tr_bullets:
        tr_lines.append("Olası Şüpheler:")
        for b in tr_bullets:
            tr_lines.append(f"• {b}")
    if left_attempts is not None:
        tr_lines.append(f"• Kalan deneme hakkı: {left_attempts}")
        
    en_lines = [en_header]
    if en_bullets:
        en_lines.append("Potential Suspicions:")
        for b in en_bullets:
            en_lines.append(f"• {b}")
    if left_attempts is not None:
        en_lines.append(f"• Remaining attempts: {left_attempts}")
        
    return "\n".join(tr_lines) + "\n\n" + "\n".join(en_lines)


# ---------------------------------------------------------------------------
# Liveness detection helper (Issue #30) — frame-subtraction tabanlı
# ---------------------------------------------------------------------------

def _check_liveness_frames(
    left_bytes: bytes,
    center_bytes: bytes,
    right_bytes: bytes,
) -> tuple:
    """
    3 açıdan alınan frame'lerle aktif liveness kontrolü yapar.

    Frame subtraction + entropi analizi kullanır (products/liveness_detection.py).
    Hiçbir derin öğrenme modeli gerektirmez.

    Args:
        left_bytes   : Sol  açı görüntüsünün ham byte içeriği.
        center_bytes : Merkez görüntünün ham byte içeriği.
        right_bytes  : Sağ  açı görüntüsünün ham byte içeriği.

    Returns:
        (is_real: bool, score: float, result: LivenessResult)
    """
    result: LivenessResult = run_liveness_check(left_bytes, center_bytes, right_bytes)

    if result.is_live:
        return True, result.score, result
    else:
        return False, result.score, result


# ---------------------------------------------------------------------------
# Throttle class for biometric login (Issue #37)
# ---------------------------------------------------------------------------
class BiometricLoginThrottle(SimpleRateThrottle):
    """
    Limits biometric login attempts to prevent brute-force attacks.
    Rate is configured in settings.DEFAULT_THROTTLE_RATES['biometric_login'].
    Keyed by client IP address.
    """
    scope = 'biometric_login'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['username'] = user.username
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def biometric_enable(request):
    """
    POST /api/biometric/enable/
    Yüz fotoğrafını alır, DeepFace ile özellik vektörünü çıkarır ve şifreli kaydeder.

    İsteğe bağlı: 3 frame (frame_left, frame_center, frame_right) gönderilirse
    aktif liveness kontrolü de yapılır.  Eğer sadece face_image gönderilirse
    liveness atlanır (geriye dönük uyumluluk).
    """
    serializer = BiometricEnableSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    face_image = request.FILES.get('face_image')
    if not face_image:
        return Response({'success': False, 'error': 'Yüz fotoğrafı gerekli. Lütfen bir fotoğraf çekin. / A face photo is required. Please take a photo.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from deepface import DeepFace

        # --- Aktif Liveness kontrolü (Issue #30) — 3 frame varsa ---
        frame_left   = request.FILES.get('frame_left')
        frame_center = request.FILES.get('frame_center')
        frame_right  = request.FILES.get('frame_right')

        if frame_left and frame_center and frame_right:
            is_real, liveness_score, liveness_error = _check_liveness_frames(
                left_bytes=frame_left.read(),
                center_bytes=frame_center.read(),
                right_bytes=frame_right.read(),
            )
            if not is_real:
                return Response(
                    {'success': False, 'error': liveness_error, 'liveness_score': liveness_score},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            logger.info("biometric_enable: 3 liveness frame gönderilmedi, liveness kontrolü atlandı.")

        # Load image into numpy array for cv2
        file_bytes = np.asarray(bytearray(face_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Extract features
        objs = DeepFace.represent(img_path=img, model_name="Facenet", enforce_detection=True)
        
        if len(objs) == 0:
            return Response({'success': False, 'error': 'Yüz algılanamadı. Lütfen yüzünüzün net göründüğünden emin olun ve tekrar deneyin. / Face could not be detected. Please make sure your face is clearly visible and try again.'}, status=status.HTTP_400_BAD_REQUEST)
            
        embedding = objs[0]["embedding"]
        user = request.user
        # Encrypt the embedding before storing (Issue #29)
        user.face_encoding = encrypt_face_encoding(embedding)
        user.biometric_enabled = True
        user.save()
        _reset_biometric_failures(user.username)
        
        return Response({
            'success': True,
            'message': 'Yüz tanıma başarıyla etkinleştirildi! Artık yüzünüzle giriş yapabilirsiniz. / Face recognition has been successfully enabled! You can now log in with your face.',
            'biometric_enabled': True
        })
    except ValueError as ve:
        return Response({'success': False, 'error': 'Yüz bulunamadı veya fotoğraf uygun değil. Lütfen iyi aydınlatılmış bir ortamda net bir fotoğraf çekin. / Face not found or photo is not suitable. Please take a clear photo in a well-lit environment.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        return Response({'success': False, 'error': 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin. / An unexpected error occurred. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([BiometricLoginThrottle])
@parser_classes([MultiPartParser, FormParser])
def biometric_login(request):
    """
    POST /api/biometric/login/
    Gelen fotoğrafın özelliklerini çıkarıp, sistemdekiyle karşılaştırır.
    Rate-limited: 5 istek/dakika (Issue #37).
    """
    serializer = BiometricLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data['username']
    face_image = request.FILES.get('face_image')
    
    try:
        user = CustomUser.objects.get(username=username)
        
        # Check if currently locked out
        remaining_lockout = _get_lockout_remaining(username)
        if remaining_lockout > 0:
            minutes = (remaining_lockout + 59) // 60
            error_msg = _format_biometric_error(
                "Giriş Başarısız\nÇok fazla başarısız deneme nedeniyle yüz tanıma kilitlendi.",
                ["Lütfen şifrenizle giriş yapın.", f"{minutes} dakika sonra tekrar deneyebilirsiniz."],
                "Login Failed\nFace recognition has been locked due to too many failed attempts.",
                ["Please log in with your password.", f"You can try again after {minutes} minutes."]
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'locked_out': True,
                    'lockout_remaining': remaining_lockout
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.biometric_enabled or not user.face_encoding:
            error_msg = _format_biometric_error(
                "Giriş Başarısız\nYüz tanıma bu hesap için henüz etkinleştirilmemiş.",
                ["Lütfen önce ayarlardan yüz tanımayı açın."],
                "Login Failed\nFace recognition is not enabled for this account.",
                ["Please enable face recognition from settings first."]
            )
            return Response({'success': False, 'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
        from deepface import DeepFace
        from deepface.modules import verification

        # --- Aktif Liveness kontrolü (Issue #30) — 3 frame varsa ---
        frame_left   = request.FILES.get('frame_left')
        frame_center = request.FILES.get('frame_center')
        frame_right  = request.FILES.get('frame_right')

        if frame_left and frame_center and frame_right:
            is_real, liveness_score, liveness_error = _check_liveness_frames(
                left_bytes=frame_left.read(),
                center_bytes=frame_center.read(),
                right_bytes=frame_right.read(),
            )
            if not is_real:
                logger.warning(
                    "Spoof attempt detected for user '%s' (liveness_score=%.4f)",
                    username, liveness_score,
                )
                left_attempts, locked, _ = _handle_biometric_failure(user)
                if locked:
                    error_msg = _format_biometric_error(
                        "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                        ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                        "Login Failed\nFace recognition has been locked for 5 minutes.",
                        ["Too many failed attempts were detected.", "Please log in with your password."]
                    )
                    return Response(
                        {
                            'success': False,
                            'error': error_msg,
                            'liveness_score': liveness_score
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                
                tr_bullets = []
                en_bullets = []
                if hasattr(liveness_error, 'details') and isinstance(liveness_error.details, dict):
                    fail_list = liveness_error.details.get("fail_reasons_list", [])
                    for tr_r, en_r in fail_list:
                        tr_bullets.append(tr_r)
                        en_bullets.append(en_r)
                if not tr_bullets:
                    tr_bullets = ["Canlılık doğrulaması başarısız oldu."]
                    en_bullets = ["Liveness verification failed."]
                
                error_msg = _format_biometric_error(
                    "Giriş Başarısız",
                    tr_bullets,
                    "Login Failed",
                    en_bullets,
                    left_attempts=left_attempts
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                        'liveness_score': liveness_score
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            logger.info("biometric_login: 3 liveness frame gönderilmedi, liveness kontrolü atlandı.")

        file_bytes = np.asarray(bytearray(face_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Extract current face embedding
        objs = DeepFace.represent(img_path=img, model_name="Facenet", enforce_detection=False)
        if len(objs) == 0:
            left_attempts, locked, _ = _handle_biometric_failure(user)
            if locked:
                error_msg = _format_biometric_error(
                    "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                    ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                    "Login Failed\nFace recognition has been locked for 5 minutes.",
                    ["Too many failed attempts were detected.", "Please log in with your password."]
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            error_msg = _format_biometric_error(
                "Giriş Başarısız",
                ["Gönderilen fotoğrafta yüz bulunamadı.", "Lütfen yüzünüzün net göründüğünden emin olun."],
                "Login Failed",
                ["No face found in the photo.", "Please make sure your face is clearly visible."],
                left_attempts=left_attempts
            )
            return Response({'success': False, 'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
        incoming_embedding = objs[0]["embedding"]
        # Decrypt stored embedding (Issue #29)
        stored_embedding = decrypt_face_encoding(user.face_encoding)
        
        # Calculate Cosine Distance
        distance = verification.find_distance(stored_embedding, incoming_embedding, distance_metric='cosine')
        threshold = verification.find_threshold(model_name="Facenet", distance_metric="cosine")
        
        # We allow a slightly lenient threshold for general usage (+0.04)
        lenient_threshold = threshold + 0.04
        
        if distance <= lenient_threshold:
            _reset_biometric_failures(username)
            tokens = get_tokens_for_user(user)
            return Response({
                'success': True,
                'message': 'Giriş başarılı! / Login successful!',
                'tokens': tokens,
                'user_id': user.id,
                'username': user.username,
                'role': user.role
            })
        else:
            left_attempts, locked, _ = _handle_biometric_failure(user)
            if locked:
                error_msg = _format_biometric_error(
                    "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                    ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                    "Login Failed\nFace recognition has been locked for 5 minutes.",
                    ["Too many failed attempts were detected.", "Please log in with your password."]
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            error_msg = _format_biometric_error(
                "Giriş Başarısız",
                ["Yüz eşleşmedi.", "Kayıtlı yüzünüzle giriş yapmayı tekrar deneyin."],
                "Login Failed",
                ["Face did not match.", "Please try again with your registered face."],
                left_attempts=left_attempts
            )
            return Response({'success': False, 'error': error_msg}, status=status.HTTP_401_UNAUTHORIZED)

    except CustomUser.DoesNotExist:
        return Response({'success': False, 'error': 'Kullanıcı bulunamadı. Lütfen kullanıcı adınızı kontrol edin. / User not found. Please check your username.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'success': False, 'error': 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin. / An unexpected error occurred. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def biometric_disable(request):
    """
    POST /api/biometric/disable/
    """
    user = request.user
    user.biometric_enabled = False
    user.face_encoding = None
    user.save()
    
    return Response({
        'success': True,
        'message': 'Yüz tanıma devre dışı bırakıldı. / Face recognition has been disabled.',
        'biometric_enabled': False
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def biometric_status(request):
    """
    GET /api/biometric/status/
    """
    user = request.user
    return Response({
        'biometric_enabled': user.biometric_enabled,
        'has_encoding': bool(user.face_encoding)
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def biometric_status_public(request):
    """
    GET /api/biometric/status-public/?username=xxx
    """
    username = request.query_params.get('username')
    if not username:
        return Response({'biometric_enabled': False}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = CustomUser.objects.get(username=username)
        return Response({
            'biometric_enabled': user.biometric_enabled and bool(user.face_encoding)
        })
    except CustomUser.DoesNotExist:
        return Response({'biometric_enabled': False})


# ---------------------------------------------------------------------------
# Aktif Liveness Check Endpoint (Issue #30)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def liveness_check(request):
    """
    POST /api/biometric/liveness-check/

    Kullanıcının başını çevirirken çekilen 3 frame'i alır ve
    frame subtraction analizi ile liveness skoru döndürür.

    Beklenen multipart/form-data alanları:
        frame_left   (file) — Sol  açı (yaw ≈ -25°)
        frame_center (file) — Merkez (yaw ≈  0°)
        frame_right  (file) — Sağ  açı (yaw ≈ +25°)

    Başarılı yanıt (HTTP 200):
        {
            "is_live": true,
            "score": 0.812,
            "reason": "Canlılık doğrulandı. ...",
            "details": { ... }   # Çift metrikler
        }

    Başarısız yanıt (HTTP 400 / 403):
        {
            "is_live": false,
            "score": 0.021,
            "reason": "Canlılık doğrulaması başarısız: ..."
        }
    """
    frame_left   = request.FILES.get('frame_left')
    frame_center = request.FILES.get('frame_center')
    frame_right  = request.FILES.get('frame_right')

    if not (frame_left and frame_center and frame_right):
        return Response(
            {
                'is_live': False,
                'score': 0.0,
                'reason': (
                    "3 farklı açıdan fotoğraf gerekli. "
                    "Lütfen başınızı yavaşça sola ve sağa çevirerek kameraya bakın. "
                    "/ 3 photos from different angles are required. "
                    "Please slowly turn your head left and right while looking at the camera."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = run_liveness_check(
            left_bytes=frame_left.read(),
            center_bytes=frame_center.read(),
            right_bytes=frame_right.read(),
        )

        response_data = {
            'is_live': result.is_live,
            'score':   result.score,
            'reason':  result.reason,
            'details': result.details,
        }

        if result.is_live:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.warning(
                "Liveness check başarısız — score=%.4f, reason=%s",
                result.score, result.reason,
            )
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        import traceback
        logger.error("liveness_check hatası: %s", traceback.format_exc())
        return Response(
            {'is_live': False, 'score': 0.0, 'reason': 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin. / An unexpected error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Video Tabanlı Liveness Check (Yeni Ana Yöntem)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def liveness_check_video(request):
    """
    POST /api/biometric/liveness-check-video/

    Kullanıcı kameraya kayıt yaparken başını çevirir (2-4 saniye).
    Video dosyası backend'e gönderilir, OpenCV ile kareler çıkarılır,
    ardışık frame subtraction ile liveness skoru hesaplanır.

    Beklenen multipart/form-data:
        video (file)  — mp4 veya mov formatında kısa video

    Başarılı yanıt (HTTP 200):
        { "is_live": true, "score": 0.85, "reason": "...", "details": {...} }

    Başarısız yanıt (HTTP 403):
        { "is_live": false, "score": 0.02, "reason": "Hareket yeterli değil..." }
    """
    video_file = request.FILES.get('video')
    if not video_file:
        return Response(
            {'is_live': False, 'score': 0.0, 'reason': "Video dosyası gerekli. Lütfen kameranızla kısa bir video çekin. / A video file is required. Please record a short video with your camera."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        video_bytes = video_file.read()
        result = run_liveness_check_from_video(video_bytes)

        response_data = {
            'is_live': result.is_live,
            'score':   result.score,
            'reason':  result.reason,
            'details': result.details,
        }

        if result.is_live:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.warning(
                "Video liveness başarısız — score=%.4f, reason=%s",
                result.score, result.reason,
            )
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        import traceback
        logger.error("liveness_check_video hatası: %s", traceback.format_exc())
        return Response(
            {'is_live': False, 'score': 0.0, 'reason': 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin. / An unexpected error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Multi-Frame Liveness Check — Video yerine JPEG dizisi (Önerilen yöntem)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([BiometricLoginThrottle])
@parser_classes([MultiPartParser, FormParser])
def biometric_login_with_liveness(request):
    """
    POST /api/biometric/login-with-liveness/

    Liveness detection ve face verification'ı TEK ADIMDA yapar.
    Bu sayede birisi liveness'ı kendi yüzüyle geçip, sonra başkasının
    fotoğrafını göstererek giriş yapma zafiyeti ortadan kalkar.

    İş akışı:
      1. Frontend 5sn boyunca her 600ms'de frame çeker (≈8 frame)
      2. Tüm frame'ler + username tek istekte gönderilir
      3. Backend:
         a) Ardışık frame subtraction → liveness skoru
         b) En iyi frame'den DeepFace embedding → kayıtlı yüzle eşleştirme
      4. İkisi de geçerse → JWT token döner

    Beklenen multipart/form-data:
        username           (text)  — Kullanıcı adı
        frame_0 ... frame_N (file) — Ardışık JPEG frame'ler (en az 3)

    Başarılı (HTTP 200):
        { "success": true, "tokens": {...}, ... }
    Başarısız (HTTP 403):
        { "success": false, "error": "..." }
    """
    username = request.data.get('username')
    if not username:
        return Response(
            {'success': False, 'error': 'Kullanıcı adı gerekli. / Username is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Frame'leri topla
    frame_bytes_list = []
    frame_files = []
    i = 0
    while True:
        f = request.FILES.get(f'frame_{i}')
        if f is None:
            break
        raw = f.read()
        frame_bytes_list.append(raw)
        frame_files.append(raw)
        i += 1
        if i >= 20:
            break

    if len(frame_bytes_list) < 3:
        return Response(
            {
                'success': False,
                'error': "Yeterli sayıda fotoğraf alınamadı. Lütfen kameranın önünde biraz daha bekleyin. / Not enough photos were captured. Please wait a bit longer in front of the camera.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Kullanıcıyı bul ve biyometrik kontrol açık mı doğrula (Önceden buluyoruz ki başarısız denemeleri takip edebilelim)
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Kullanıcı bulunamadı. Lütfen kullanıcı adınızı kontrol edin. / User not found. Please check your username.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if currently locked out
        remaining_lockout = _get_lockout_remaining(username)
        if remaining_lockout > 0:
            minutes = (remaining_lockout + 59) // 60
            error_msg = _format_biometric_error(
                "Giriş Başarısız\nÇok fazla başarısız deneme nedeniyle yüz tanıma kilitlendi.",
                ["Lütfen şifrenizle giriş yapın.", f"{minutes} dakika sonra tekrar deneyebilirsiniz."],
                "Login Failed\nFace recognition has been locked due to too many failed attempts.",
                ["Please log in with your password.", f"You can try again after {minutes} minutes."]
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'locked_out': True,
                    'lockout_remaining': remaining_lockout
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.biometric_enabled or not user.face_encoding:
            error_msg = _format_biometric_error(
                "Giriş Başarısız\nYüz tanıma bu hesap için henüz etkinleştirilmemiş.",
                ["Lütfen önce ayarlardan yüz tanımayı açın."],
                "Login Failed\nFace recognition is not enabled for this account.",
                ["Please enable face recognition from settings first."]
            )
            return Response(
                {'success': False, 'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Adım 1: Liveness kontrolü (frame subtraction) ──────────────
        liveness_result = run_liveness_check_multiframe(frame_bytes_list)

        if not liveness_result.is_live:
            logger.warning(
                "Liveness başarısız — user='%s', score=%.4f, reason=%s",
                username, liveness_result.score, liveness_result.reason,
            )
            left_attempts, locked, _ = _handle_biometric_failure(user)
            if locked:
                error_msg = _format_biometric_error(
                    "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                    ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                    "Login Failed\nFace recognition has been locked for 5 minutes.",
                    ["Too many failed attempts were detected.", "Please log in with your password."]
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                        'liveness_score': liveness_result.score,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            tr_bullets = []
            en_bullets = []
            if hasattr(liveness_result, 'details') and isinstance(liveness_result.details, dict):
                fail_list = liveness_result.details.get("fail_reasons_list", [])
                for tr_r, en_r in fail_list:
                    tr_bullets.append(tr_r)
                    en_bullets.append(en_r)
            if not tr_bullets:
                tr_bullets = ["Canlılık doğrulaması başarısız oldu."]
                en_bullets = ["Liveness verification failed."]

            error_msg = _format_biometric_error(
                "Giriş Başarısız",
                tr_bullets,
                "Login Failed",
                en_bullets,
                left_attempts=left_attempts
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'liveness_score': liveness_result.score,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Adım 2: Face verification (AYNI frame'lerden biriyle) ──────
        # Ortadaki frame'i seç (en düz bakış açısı olma ihtimali yüksek)
        mid_idx = len(frame_bytes_list) // 2
        face_bytes = frame_bytes_list[mid_idx]

        from deepface import DeepFace
        from deepface.modules import verification

        # Ortadaki frame'den embedding çıkar
        face_arr = np.frombuffer(face_bytes, dtype=np.uint8)
        face_img = cv2.imdecode(face_arr, cv2.IMREAD_COLOR)
        if face_img is None:
            left_attempts, locked, _ = _handle_biometric_failure(user)
            if locked:
                error_msg = _format_biometric_error(
                    "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                    ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                    "Login Failed\nFace recognition has been locked for 5 minutes.",
                    ["Too many failed attempts were detected.", "Please log in with your password."]
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                        'liveness_score': liveness_result.score,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            error_msg = _format_biometric_error(
                "Giriş Başarısız",
                ["Fotoğraf işlenemedi. Lütfen tekrar deneyin."],
                "Login Failed",
                ["Photo could not be processed. Please try again."],
                left_attempts=left_attempts
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'liveness_score': liveness_result.score,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        objs = DeepFace.represent(img_path=face_img, model_name="Facenet", enforce_detection=False)
        if len(objs) == 0:
            left_attempts, locked, _ = _handle_biometric_failure(user)
            if locked:
                error_msg = _format_biometric_error(
                    "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                    ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                    "Login Failed\nFace recognition has been locked for 5 minutes.",
                    ["Too many failed attempts were detected.", "Please log in with your password."]
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                        'liveness_score': liveness_result.score,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            error_msg = _format_biometric_error(
                "Giriş Başarısız",
                ["Fotoğraflarda yüz bulunamadı. Lütfen yüzünüzün net göründüğünden emin olun."],
                "Login Failed",
                ["No face found in the photos. Please make sure your face is clearly visible."],
                left_attempts=left_attempts
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'liveness_score': liveness_result.score,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        incoming_embedding = objs[0]["embedding"]
        stored_embedding = decrypt_face_encoding(user.face_encoding)

        distance = verification.find_distance(stored_embedding, incoming_embedding, distance_metric='cosine')
        threshold = verification.find_threshold(model_name="Facenet", distance_metric="cosine")
        lenient_threshold = threshold + 0.04

        logger.info(
            "LoginWithLiveness → user=%s, distance=%.4f, threshold=%.4f, lenient=%.4f, liveness_score=%.4f",
            username, distance, threshold, lenient_threshold, liveness_result.score,
        )

        if distance > lenient_threshold:
            left_attempts, locked, _ = _handle_biometric_failure(user)
            if locked:
                error_msg = _format_biometric_error(
                    "Giriş Başarısız\nYüz tanıma 5 dakika süreyle kilitlendi.",
                    ["Çok fazla başarısız deneme gerçekleştirildi.", "Lütfen şifrenizle giriş yapın."],
                    "Login Failed\nFace recognition has been locked for 5 minutes.",
                    ["Too many failed attempts were detected.", "Please log in with your password."]
                )
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                        'liveness_score': liveness_result.score,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            error_msg = _format_biometric_error(
                "Giriş Başarısız",
                ["Canlılık doğrulandı ancak yüz eşleşmedi. Lütfen kayıtlı yüzünüzle tekrar deneyin."],
                "Login Failed",
                ["Liveness verified but face did not match. Please try again with your registered face."],
                left_attempts=left_attempts
            )
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'liveness_score': liveness_result.score,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Her iki kontrol de geçti → token üret ──────────────────────
        _reset_biometric_failures(username)
        tokens = get_tokens_for_user(user)
        return Response({
            'success': True,
            'message': 'Giriş başarılı! / Login successful!',
            'tokens': tokens,
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'liveness_score': liveness_result.score,
        })

    except Exception as e:
        import traceback
        logger.error("biometric_login_with_liveness hatası: %s", traceback.format_exc())
        return Response(
            {'success': False, 'error': 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin. / An unexpected error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def liveness_check_multi(request):
    """
    POST /api/biometric/liveness-check-multi/

    Frontend 5 saniye boyunca her 500ms'de bir fotoğraf çeker (≈10 frame),
    bunları frame_0, frame_1, ... adlarıyla multipart olarak gönderir.
    Backend ardışık frame subtraction ile liveness skoru hesaplar.

    Video codec sorununu tamamen ortadan kaldırır.

    Beklenen multipart/form-data:
        frame_0, frame_1, ..., frame_N  (JPEG, en az 3, en fazla 20)

    Başarılı (HTTP 200):
        { "is_live": true, "score": 0.87, "reason": "...", "details": {...} }
    Başarısız (HTTP 403):
        { "is_live": false, "score": 0.01, "reason": "Hareket yeterli değil..." }
    """
    # frame_0, frame_1, ... adlarıyla sıralı dosyaları topla
    frame_bytes_list = []
    i = 0
    while True:
        f = request.FILES.get(f'frame_{i}')
        if f is None:
            break
        frame_bytes_list.append(f.read())
        i += 1
        if i >= 20:   # Maks 20 frame
            break

    if len(frame_bytes_list) < 3:
        return Response(
            {
                'is_live': False, 'score': 0.0,
                'reason': "Yeterli sayıda fotoğraf alınamadı. Lütfen kameranın önünde biraz daha bekleyin. / Not enough photos were captured. Please wait a bit longer in front of the camera.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = run_liveness_check_multiframe(frame_bytes_list)

        response_data = {
            'is_live': result.is_live,
            'score':   result.score,
            'reason':  result.reason,
            'details': result.details,
        }

        if result.is_live:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.warning(
                "Multi-frame liveness başarısız — score=%.4f, frames=%d, reason=%s",
                result.score, len(frame_bytes_list), result.reason,
            )
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        import traceback
        logger.error("liveness_check_multi hatası: %s", traceback.format_exc())
        return Response(
            {'is_live': False, 'score': 0.0, 'reason': 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin. / An unexpected error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
