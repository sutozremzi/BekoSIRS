# products/ml_recommender.py
# ==============================================================================
# BEKOSIRS HİBRİT ÖNERİ SİSTEMİ (RECOMMENDATION ENGINE) TEKNİK REFERANS REHBERİ
# ==============================================================================
#
# ADIM 1: GİRDİ VERİLERİ VE ETKİLEŞİM AĞIRLIKLARI
#
# Ağırlık hiyerarşisi (5 > 3 > ★ > 1), implicit feedback literatüründe yerleşik
# "confidence" yaklaşımına dayanır (Hu, Koren & Volinsky, 2008 — "Collaborative
# Filtering for Implicit Feedback Datasets", ICDM). Temel prensip: bir kullanıcı
# bir ürünü ne kadar güçlü bir niyet sinyaliyle edinmişse, modelin o (kullanıcı,ürün)
# çiftine verdiği güven (confidence) de o ölçüde yüksek olmalıdır.
#
#   Satın Alma (5.0): Nakit harcama = en güçlü tercih kanıtı. Koren et al. (2009)
#     "Matrix Factorization Techniques for Recommender Systems" (IEEE Computer)
#     çalışmasında açık derecelendirme yerine satın alma gibi örtük sinyalin
#     daha güvenilir olduğu gösterilmiştir.
#   İstek Listesi (3.0): "Almak istiyorum" niyeti; satın almadan düşük, görüntülemeden
#     yüksek. Pan et al. (2008) "One-Class Collaborative Filtering" (ICDM) bu ara
#     sinyal türünü ayrı bir güven seviyesiyle modellemektedir.
#   Yorum (★ kadar): Kullanıcının bilinçli verdiği geri bildirim; yıldız sayısı
#     doğal ağırlık sağlar. Asgari eşik (>3 yıldız) ile negatif deneyimler
#     pozitif sinyal havuzuna karışmaz.
#   Görüntüleme (1.0, max 5): Zayıf niyet sinyali — merak ya da kazara tıklama
#     olabilir. Cap (5) aşırı görüntüleme gürültüsünü sınırlandırır; bu strateji
#     Hu et al. (2008) §4.1 "uniform confidence" tartışmasıyla örtüşmektedir.

# ------------------------------------------------------------------------------
# 1.1. Etkileşim Puanları (İki farklı yerde hesaplanır):
#   - Satın Alma (Purchase): 5.0 Puan (En güçlü sinyal)
#   - Yorum (Review): Verilen yıldız puanı kadar (Modelde), Canlı puanda sadece >3 yıldız olanlar.
#   - İstek Listesi (Wishlist): 3.0 Puan
#   - Görüntüleme (View):
#       * NCF Eğitimi için: Görüntüleme sayısı kadar, maksimum 5 ile sınırlandırılır (Cap).
#       * Canlı İçerik Puanı için: Görüntüleme sayısı kadar, maksimum 15 ile sınırlandırılır.
#   - Reddedilen Öneriler (Dismissed): -3.0 Puan (Sadece canlı puanlamada eksi sinyal olarak).
#
# 1.2. Ürün Metin Verisi (Content):
#   - İsim + Açıklama + Marka + (Kategori Adı x 3) birleştirilerek tek metin yapılır. 
#   - Kategori isminin 3 kez yazılması, kategori ağırlığını yapay zeka gözünde artırır.
#
# ADIM 2: MODELLERİN EĞİTİLMESİ VE MATEMATİKSEL HESAPLAMALAR
# ------------------------------------------------------------------------------
# 2.1. Neural Collaborative Filtering (NCF) - Yapay Sinir Ağı:
#   - Mimari: Scikit-learn MLPRegressor (128 -> 64 -> 32 -> 16 -> 1 nöronlu ReLU ağ).
#   - Modele Giren 14 Özellik (Feature Vector):
#       1. Kategori (Label Encoded)
#       2. Fiyat / Ortalama Fiyat (Normalize Fiyat)
#       3. Fiyat Sepeti (0-4 arası, Price Bucket)
#       4. Kullanıcının verdiği/aldığı ortalama puan
#       5. Kullanıcının toplam etkileşim sayısı
#       6. Kullanıcının puanlarının standart sapması
#       7. Kullanıcının etkileşime girdiği benzersiz ürün sayısı
#       8. Ürünün sitedeki ortalama yıldız puanı
#       9. Ürüne yapılan toplam yorum sayısı
#      10. Ürünün toplam görüntülenme sayısı
#      11. Ürünün toplam satın alınma sayısı
#      12. Ürünün kaç kişinin istek listesinde olduğu
#      13. Kullanıcı - Kategori Yakınlığı (Kullanıcı bu kategoriyle ne kadar ilgili?)
#      14. Kullanıcının özel olarak bu ürünü kaç kez görüntülediği.
#   - Tüm bu veriler MinMaxScaler ile 0-1 arasına çekilip ağa sokulur.
#
# 2.2. İçerik Tabanlı Filtreleme (Content-Based - TF-IDF & Kosinüs Benzerliği):
#   Teknik olarak "Bag-of-N-Grams" temsilidir: TF-IDF, her belgeyi kelime (1-gram)
#   ve iki-kelimelik öbek (2-gram) frekanslarına göre ağırlıklandırılmış bir
#   vektöre dönüştürür. Salton & Buckley (1988) tarafından tanımlanan TF-IDF
#   (term frequency–inverse document frequency) formülü, nadir ama ayırt edici
#   kelimelere daha yüksek ağırlık vererek saf Bag-of-Words'ün frekans yanlılığını
#   giderir (Jones, 1972 — "A Statistical Interpretation of Term Specificity").
#   N-gram aralığı (1,2) seçildi: tek kelimeler genel semantiği, ikili kelime öbekleri
#   ise "çamaşır makinesi" gibi ürüne özgü ifadeleri yakalar.
#   - TF-IDF Vectorizer en çok geçen 5000 kelime/ikili kelime grubunu (1-2 ngram) çıkarır.
#   - Ürünler arası Kosinüs Benzerliği (Cosine Similarity) hesaplanır.
#   - Kategori Bonusu: Eğer iki ürün aynı kategorideyse, benzerlik skorlarına statik +0.15 eklenir.
#
# 2.3. Popülerlik (Cold-Start / Yedek Sistem):
#   - Formül: (Toplam Görüntüleme x 1) + (Toplam Yorum x 3) + (Toplam Satın Alma x 5)
#
# ADIM 3: CANLI PUANLAMA VE BONUS HESAPLAMALARI (Kullanıcı İstek Attığında)
# ------------------------------------------------------------------------------
# 1. Ham Skorların Çekilmesi ve Normalize Edilmesi:
#   - NCF, Content ve Popülerlik modellerinden gelen skorlar kendi içlerindeki en yüksek değere (max) 
#     bölünerek 0 ile 1 arasına (Normalize) çekilir.
# 
# 2. Hibrit Formül Ağırlıkları (Adaptif — kullanıcı derinliğine göre):
#   - Soğuk başlangıç (0 etkileşim): %0 MF + %0 II + %25 Content + %75 Popularity
#   - Light (1-4 etkileşim):        %10 MF + %25 II + %30 Content + %35 Popularity
#   - Balanced (5-19 etkileşim):    %25 MF + %30 II + %30 Content + %15 Popularity
#   - Aktif (20+ etkileşim):        %35 MF + %35 II + %25 Content + %5 Popularity
#   Kademeli geçiş, Burke (2002) "Hybrid Recommender Systems" (UMUAI) çalışmasında
#   önerilen "switching hybrid" stratejisine karşılık gelir: veri yetersizse
#   model-tabanlı CF yerine non-personalized yöntemlere geçiş yapılır.
#   tune_hybrid_weights() metodu bu varsayılan ağırlıkları NDCG@K bazlı grid
#   search ile doğrulayıp gerekirse optimize eder.
#
# 3. Anlık Bonuslar (Boosts):
#   - Arama Bonusu (Search Boost): Kullanıcının son 5 araması ürünün TF-IDF metninde geçiyorsa,
#     ürünün nihai puanına DİREKT +2.0 eklenir.
#   - Fiyat Duyarlılığı Bonusu (Price Sensitivity Boost): Kullanıcının daha önce aldığı ve baktığı 
#     ürünlerin ortalama fiyatı (avg_price) bulunur. Eğer aday ürünün fiyatı bu ortalamanın 
#     %70'i ile %130'u arasındaysa, nihai puana +0.5 eklenir.
#
# ADIM 4: FİLTRELEME, DİVERSİFİKASYON VE KULLANICIYA SUNUM
# ------------------------------------------------------------------------------
# - Kesin Elemeler: Kullanıcının daha önce satın aldığı ürünler listeden tamamen çıkartılır.
# - Kategori Kısıtlaması (Diversity):
#   * Sistemin tek tip ürün önermemesi için aynı kategoriden en fazla 4 ürün alınır.
#   * Sadece kullanıcının geçmişte etkileşime girdiği (tıkladığı, aldığı vb.) kategorilerdeki
#     ürünler listeye dahil edilir. 
#   * Eğer listede yeterli (Top-N) ürün kalmazsa, bu kısıtlama esnetilir ve diğer kategoriler açılır.
# - Etiketleme (Reasoning): Ürünün puanı en çok nereden geldiyse veya hangi bonusu aldıysa,
#   "Aramalarınıza göre", "Bütçenize uygun", "[Kategori] beğenenler bunu da beğendi" gibi dinamik metinler üretilir.
#
# KAYNAKÇA
# ------------------------------------------------------------------------------
# [1] Hu, Y., Koren, Y. & Volinsky, C. (2008). Collaborative Filtering for
#     Implicit Feedback Datasets. ICDM 2008.
#     → Etkileşim ağırlık hiyerarşisi (satın alma > wishlist > görüntüleme) ve
#       "confidence" yaklaşımının temeli.
#
# [2] Koren, Y., Bell, R. & Volinsky, C. (2009). Matrix Factorization Techniques
#     for Recommender Systems. IEEE Computer, 42(8), 30-37.
#     → TruncatedSVD ile latent faktör öğrenmesi; örtük sinyalin güvenilirliği.
#
# [3] Pan, R. et al. (2008). One-Class Collaborative Filtering. ICDM 2008.
#     → Wishlist gibi ara sınıf sinyallerin ayrı güven seviyesiyle modellenmesi.
#
# [4] Salton, G. & Buckley, C. (1988). Term-Weighting Approaches in Automatic
#     Text Retrieval. Information Processing & Management, 24(5), 513-523.
#     → TF-IDF formülünün orijinal tanımı.
#
# [5] Jones, K. S. (1972). A Statistical Interpretation of Term Specificity and
#     Its Application in Retrieval. Journal of Documentation, 28(1), 11-21.
#     → IDF (Inverse Document Frequency) bileşeninin teorik gerekçesi.
#
# [6] Burke, R. (2002). Hybrid Recommender Systems: Survey and Experiments.
#     User Modeling and User-Adapted Interaction, 12(4), 331-370.
#     → Switching hybrid stratejisi: veri yetersizliğinde CF yerine non-kişisel yöntemlere geçiş.
#
# [7] Cremonesi, P., Koren, Y. & Turrin, R. (2010). Performance of Recommender
#     Algorithms on Top-N Recommendation Tasks. RecSys 2010.
#     → Leave-One-Out @K değerlendirme protokolü (Recall@K, NDCG@K).
#
# [8] Adomavicius, G. & Tuzhilin, A. (2005). Toward the Next Generation of
#     Recommender Systems. IEEE Transactions on Knowledge and Data Engineering,
#     17(6), 734-749.
#     → Hibrit ağırlık optimizasyonu için grid search gerekçesi.
#
# [9] Hidasi, B. et al. (2015). Session-based Recommendations with Recurrent
#     Neural Networks. ICLR 2016 (arXiv:1511.06939).
#     → Çevrimiçi CTR ölçümünün temel online değerlendirme metriği olarak kullanımı.
# ==============================================================================
import math
import os
import time
import threading
import logging
import warnings
from datetime import date as dt_date, datetime as dt_datetime, time as dt_time, timedelta, timezone as dt_timezone

import numpy as np
import pandas as pd
import joblib
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore', category=FutureWarning)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_MODELS_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
NCF_MODEL_PATH = os.path.join(ML_MODELS_DIR, 'ncf_model.pkl')
CONTENT_MODEL_PATH = os.path.join(ML_MODELS_DIR, 'content_model.pkl')
ENCODERS_PATH = os.path.join(ML_MODELS_DIR, 'encoders.pkl')
METRICS_PATH = os.path.join(ML_MODELS_DIR, 'metrics.pkl')
# Item-item CF (Amazon tarzi "bunu alanlar sunu da aldi") komsuluk matrisi.
# Ayri bir dosyada tutulur cunku MF/content modellerinden bagimsiz egitilip yuklenir.
ITEMITEM_MODEL_PATH = os.path.join(ML_MODELS_DIR, 'itemitem_model.pkl')


# ---------------------------------------------------------------------------
# Zamana duyarli puan yardimcilari
# ---------------------------------------------------------------------------
def temporal_weight(interaction_date, half_life_days=30):
    """
    Zamana duyarli bir etkilesim icin ustel curume katsayisi hesaplar.

    Args:
        interaction_date: Etkilesimin olustugu tarih ya da zaman damgasi.
        half_life_days: Katkinin yarilanacagi gun sayisi. Ornegin 30 ise
            30 gunluk bir etkilesim 0.5 agirlik alir.

    Yari omur tabanli ustel curume secildi cunku keskin bir esik koymak yerine
    etkilesimi yumusak sekilde azaltir ve "her 30 gunde yariya iner" diye
    urun ekiplerine kolayca anlatilabilir.
    """
    # Bazi eski kayitlarda zaman damgasi olmayabilir; gecerli bir sinyali
    # tamamen silmek yerine tam agirlik vermek daha emniyetli bir varsayimdir.
    if interaction_date is None:
        return 1.0

    normalized_date = interaction_date
    if isinstance(normalized_date, dt_date) and not isinstance(normalized_date, dt_datetime):
        # Satin alma kayitlari yalnizca gun tuttugu icin tum veri tiplerini
        # ayni formulde kullanabilmek adina gun basina normalize ediyoruz.
        normalized_date = dt_datetime.combine(normalized_date, dt_time.min)

    if normalized_date.tzinfo is None:
        # Tum tarihler ayni saat diliminde olmali; aksi halde ayni veri farkli
        # ortamlarda farkli yari omur sonucuna gidebilir.
        normalized_date = normalized_date.replace(tzinfo=dt_timezone.utc)

    now = dt_datetime.now(dt_timezone.utc)
    days_old = max(0, (now - normalized_date).days)

    # Ustel curume formulu: exp(-ln(2) * gun_sayisi / yari_omur)
    # Ornek: yari omur 30 ise 30 gunluk etkilesim 0.5, 60 gunluk etkilesim 0.25 olur.
    return math.exp(-math.log(2) * days_old / half_life_days)


# ---------------------------------------------------------------------------
# Database Sync Helpers (for shared model storage via Supabase PostgreSQL)
# ---------------------------------------------------------------------------
def _save_model_to_db(file_path):
    """Upload a local model file to the MLModelStore database table."""
    try:
        from .models import MLModelStore
        file_name = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            data = f.read()
        MLModelStore.objects.update_or_create(
            name=file_name,
            defaults={'data': data}
        )
        logger.info("Synced %s to database (%.1f KB)", file_name, len(data) / 1024)
    except Exception as e:
        logger.warning("Could not sync %s to database: %s", file_path, e)


def _load_model_from_db(file_path):
    """Download a model file from the MLModelStore database table to local disk."""
    try:
        from .models import MLModelStore
        file_name = os.path.basename(file_path)
        record = MLModelStore.objects.filter(name=file_name).first()
        if record and record.data:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(bytes(record.data))
            logger.info("Downloaded %s from database (%.1f KB)", file_name, len(record.data) / 1024)
            return True
        return False
    except Exception as e:
        logger.warning("Could not load %s from database: %s", file_path, e)
        return False

# ═══════════════════════════════════════════════════════════════════════════
# 1. MATRIX FACTORIZATION (COLLABORATIVE FILTERING) MODEL
# ═══════════════════════════════════════════════════════════════════════════
class MatrixFactorizationModel:
    """
    Matrix Factorization — Netflix Prize tarzi gercek collaborative filtering.

    Kullanici x urun implicit-feedback matrisini (R) kurar ve TruncatedSVD ile
    dusuk-rank latent faktorlere ayirir:

        R ≈ user_factors @ item_factors.T
        skor(u, i) = user_factors[u] . item_factors[i]

    Onceki "NCF" (MLPRegressor) adina ragmen user/item embedding icermiyordu,
    yani gercek CF yapamiyordu; ayrica fitted MLP pickle'i numpy surum degisiminde
    bozuluyordu (loglardaki MT19937 hatasi). SVD ile elde edilen latent vektorler
    hem gercek CF saglar hem de duz numpy dizisi olarak kaydedildigi icin yukleme
    surum-bagimsiz ve dayaniklidir.

    Sinif adi geriye donuk uyumluluk icin `NCFModel` alias'i ile de erisilebilir.
    """

    # Latent faktor sayisi ust siniri. Kucuk/seyrek veride asiri ogrenmeyi onlemek
    # icin kullanici ve urun sayisindan da kucuk olacak sekilde kirpilir.
    MAX_COMPONENTS = 24

    # Implicit etkilesim agirliklari (eski NCF ile ayni semantik): satin alma en guclu.
    SIGNAL_WEIGHTS = {
        'purchase': 5.0,
        'wishlist': 3.0,
        'view': 1.0,   # view_count ile olceklenir, VIEW_COUNT_CAP ile sinirli
    }
    VIEW_COUNT_CAP = 5

    def __init__(self):
        self.user_factors = None     # np.ndarray (n_users x k)
        self.item_factors = None     # np.ndarray (n_items x k)
        self.user_index = None       # dict {user_id: satir_idx}
        self.item_ids = None         # list[int] — item_factors satir sirasi
        self.item_index = None       # dict {product_id: satir_idx}
        self.is_trained = False
        self.training_metrics = {}

    def _build_interaction_matrix(self, exclude_edges=None):
        """
        Tum (kullanici, urun) implicit etkilesimlerini {(uid, pid): skor} olarak toplar.

        Ayni cift birden cok sinyal alabilir (ornegin hem goruntuleme hem satin alma);
        skorlar toplanir, boylece guclu sinyaller matriste daha yuksek deger uretir.

        `exclude_edges`: leave-one-out degerlendirmesinde sizinti olmasin diye
        modelden gizlenecek (user_id, product_id) ciftleri. Verilirse o cift hicbir
        sinyal tipinde matrise eklenmez (urun o kullanici icin "gorulmemis" sayilir).
        """
        from .models import ViewHistory, WishlistItem, Review, ProductOwnership

        exclude_edges = exclude_edges or set()
        cells = {}

        def add(uid, pid, score):
            if uid is None or pid is None:
                return
            if (uid, pid) in exclude_edges:
                return
            cells[(uid, pid)] = cells.get((uid, pid), 0.0) + score

        for v in ViewHistory.objects.values('customer_id', 'product_id', 'view_count'):
            capped = min(v['view_count'] or 1, self.VIEW_COUNT_CAP)
            add(v['customer_id'], v['product_id'], self.SIGNAL_WEIGHTS['view'] * capped)

        for w in WishlistItem.objects.filter(
            wishlist__customer__isnull=False
        ).values('wishlist__customer_id', 'product_id'):
            add(w['wishlist__customer_id'], w['product_id'], self.SIGNAL_WEIGHTS['wishlist'])

        for r in Review.objects.values('customer_id', 'product_id', 'rating'):
            add(r['customer_id'], r['product_id'], float(r['rating']))

        for p in ProductOwnership.objects.values('customer_id', 'product_id'):
            add(p['customer_id'], p['product_id'], self.SIGNAL_WEIGHTS['purchase'])

        return cells

    def train(self, epochs=None, verbose=True, exclude_edges=None):
        """
        Implicit matrisi TruncatedSVD ile faktorize eder.

        `epochs` parametresi yalnizca eski NCF imzasiyla uyumluluk icin durur ve
        yok sayilir (SVD iteratif epoch kullanmaz). `exclude_edges` leave-one-out
        degerlendirmesinde holdout kenarlarini gizlemek icin kullanilir.
        """
        cells = self._build_interaction_matrix(exclude_edges=exclude_edges)
        if not cells or len(cells) < 5:
            msg = "Not enough interaction data to train MF (need at least 5 interactions)"
            if verbose:
                print(msg)
            logger.warning(msg)
            self.is_trained = False
            return False

        user_ids = sorted({uid for uid, _ in cells})
        item_ids = sorted({pid for _, pid in cells})
        self.user_index = {uid: i for i, uid in enumerate(user_ids)}
        self.item_index = {pid: i for i, pid in enumerate(item_ids)}
        self.item_ids = item_ids

        n_users, n_items = len(user_ids), len(item_ids)

        if verbose:
            print("Loading interaction data...")
            print(f"   Found {len(cells)} user-product interactions")
            print(f"   Unique users: {n_users}, unique products: {n_items}")

        # Yogun matris kucuk katalogda sorun degil (263 x 32 ≈ 8K hucre).
        R = np.zeros((n_users, n_items), dtype=float)
        for (uid, pid), score in cells.items():
            R[self.user_index[uid], self.item_index[pid]] = score

        # Latent boyut, SVD'nin gerektirdigi gibi min(n_users, n_items)'tan kucuk olmali.
        # Ayrica kasitli olarak tam-rank'in iyice altinda tutulur: aksi halde kucuk
        # kullanici matrisinde SVD veriyi EZBERLER (generalize etmez) ve hem oneriler
        # zayiflar hem de offline siralama metrikleri yaniltici sekilde mukemmel cikar.
        # min(n_users, n_items)//2 tavani bu ezberlemeyi engelleyip gercek latent yapiyi
        # ogrenmeye zorlar.
        rank_cap = max(2, min(n_users, n_items) // 2)
        k = max(2, min(self.MAX_COMPONENTS, rank_cap, n_users - 1, n_items - 1))

        svd = TruncatedSVD(n_components=k, random_state=42)
        # user_factors: her kullanicinin latent zevk vektoru.
        self.user_factors = svd.fit_transform(R)
        # item_factors: her urunun latent ozellik vektoru (components_ transpoze).
        self.item_factors = svd.components_.T

        # Aciklanan varyans, dusuk-rank latent uzayin matrisi ne kadar tasidigini ozetler.
        explained_variance = float(svd.explained_variance_ratio_.sum())

        self.training_metrics = {
            'algorithm': 'TruncatedSVD',
            'n_components': k,
            'explained_variance': round(explained_variance, 4),
            'n_interactions': len(cells),
            'n_users': n_users,
            'n_products': n_items,
            'trained_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        self.is_trained = True

        if verbose:
            print("\nMatrix Factorization (TruncatedSVD) trained:")
            print(f"   Matrix: {n_users} users x {n_items} products")
            print(f"   Latent factors (k): {k}")
            print(f"   Explained variance: {explained_variance:.4f}")

        return True

    def predict_for_user(self, user_id, all_product_ids, products_df=None):
        """
        Kullanici icin tum urunlere latent dot-product skoru hesaplar.

        `products_df` parametresi eski NCF imzasiyla uyumluluk icin durur; SVD
        skorlamasi yalnizca latent faktorleri kullandigindan kullanilmaz.
        Egitimde gorulmemis kullanici (cold-start) icin bos sozluk doner; bu durumda
        hibrit motor populerlik/content kulesine yaslanir.
        """
        if not self.is_trained or self.user_factors is None:
            return {}

        u_idx = self.user_index.get(user_id)
        if u_idx is None:
            return {}

        # (n_items x k) @ (k,) → (n_items,) tek vektorize carpim.
        raw = self.item_factors @ self.user_factors[u_idx]

        requested = set(all_product_ids) if all_product_ids is not None else None
        scores = {}
        for j, pid in enumerate(self.item_ids):
            if requested is not None and pid not in requested:
                continue
            value = float(raw[j])
            # Negatif latent skorlar zayif/ilgisiz sinyaldir; yalnizca pozitifleri tutariz.
            if value > 0:
                scores[pid] = value
        return scores

    def save(self, path=None):
        """Latent faktorleri diske ve paylasimli veritabanina kaydeder (duz numpy → guvenli)."""
        os.makedirs(ML_MODELS_DIR, exist_ok=True)
        save_path = path or NCF_MODEL_PATH
        joblib.dump({
            'user_factors': self.user_factors,
            'item_factors': self.item_factors,
            'user_index': self.user_index,
            'item_index': self.item_index,
            'item_ids': self.item_ids,
            'metrics': self.training_metrics,
        }, save_path)
        joblib.dump(self.training_metrics, METRICS_PATH)
        logger.info("MF model saved to %s", ML_MODELS_DIR)

        for file_path in [save_path, METRICS_PATH]:
            _save_model_to_db(file_path)

    def load(self, path=None):
        """
        Diskten (yoksa veritabanindan) yukler.

        Yalnizca duz numpy dizileri saklandigi icin yukleme surum-bagimsizdir; eski
        MLPRegressor pickle'i veya bozuk dosya gelirse istisna yakalanir ve False
        donulur, boylece motor yeniden egitime gecer.
        """
        model_path = path or NCF_MODEL_PATH

        if not os.path.exists(model_path):
            logger.info("Local MF model file missing, trying database...")
            _load_model_from_db(model_path)
            _load_model_from_db(METRICS_PATH)

        if not os.path.exists(model_path):
            return False

        try:
            data = joblib.load(model_path)
            self.user_factors = data['user_factors']
            self.item_factors = data['item_factors']
            self.user_index = data['user_index']
            self.item_index = data['item_index']
            self.item_ids = data['item_ids']
            self.training_metrics = data.get('metrics', {})
            self.is_trained = (
                self.user_factors is not None and self.item_factors is not None
            )
            if self.is_trained:
                logger.info("MF model loaded from %s", model_path)
            return self.is_trained
        except Exception as e:
            logger.error("Failed to load MF model: %s", e)
            return False


# Geriye donuk uyumluluk: eski isimle import eden kodlar (testler, management komutlari)
# kirilmasin diye NCFModel artik MatrixFactorizationModel'e isaret eder.
NCFModel = MatrixFactorizationModel


# ═══════════════════════════════════════════════════════════════════════════
# 2. CONTENT-BASED FILTERING MODEL
# ═══════════════════════════════════════════════════════════════════════════
class ContentBasedModel:
    """
    Content-Based filtering using TF-IDF similarity.
    
    Builds a text profile for each product from name + description + brand +
    category, then computes cosine similarity between all product pairs.
    
    Enhancement over the original:
    - Category-aware weighting (same-category products get a boost)
    - Price-range similarity incorporated
    """

    def __init__(self):
        self.similarity_matrix = None
        self.products_df = None
        self.indices = None
        self.tfidf_matrix = None
        self.is_trained = False

    def train(self, verbose=True):
        """Build the content similarity matrix from all products."""
        from .models import Product

        if verbose:
            print("\nTraining Content-Based model...")

        products = Product.objects.all().values(
            'id', 'name', 'description', 'brand', 'category__name', 'price'
        )
        self.products_df = pd.DataFrame(list(products))

        if self.products_df.empty:
            if verbose:
                print("   Warning: no products found in database")
            return False

        # Build composite text feature — weight category more heavily
        self.products_df['content'] = (
            self.products_df['name'].fillna('') + " " +
            self.products_df['description'].fillna('') + " " +
            self.products_df['brand'].fillna('') + " " +
            # Repeat category 3x for higher weight
            (self.products_df['category__name'].fillna('') + " ") * 3
        ).str.lower().str.strip()

        self.products_df['price'] = pd.to_numeric(
            self.products_df['price'], errors='coerce'
        ).fillna(0)

        # Build TF-IDF vectors
        tfidf = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),  # Unigrams + bigrams for richer features
            min_df=1,
            max_df=0.95,
        )
        self.tfidf_matrix = tfidf.fit_transform(self.products_df['content'])

        # Compute cosine similarity
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)

        # Category boost: products in the same category get +0.15 similarity
        # Vectorized: build a boolean mask of same-category pairs, apply boost at once
        categories = self.products_df['category__name'].values
        n = len(categories)
        # Group indices by category for efficient pair matching
        cat_groups = {}
        for idx, cat in enumerate(categories):
            if cat:
                cat_groups.setdefault(cat, []).append(idx)
        for indices in cat_groups.values():
            if len(indices) > 1:
                ix = np.array(indices)
                # Use numpy advanced indexing: boost all (i, j) pairs within same category
                row_idx = np.repeat(ix, len(ix))
                col_idx = np.tile(ix, len(ix))
                mask = row_idx != col_idx  # skip diagonal
                self.similarity_matrix[row_idx[mask], col_idx[mask]] += 0.15

        # Build product index mapping
        self.indices = pd.Series(
            self.products_df.index,
            index=self.products_df['id']
        ).drop_duplicates()

        self.is_trained = True

        if verbose:
            print(f"   Built similarity matrix for {len(self.products_df)} products")
            print(f"   TF-IDF features: {self.tfidf_matrix.shape[1]}")

        return True

    def get_similar_products(self, product_id, top_n=10):
        """Get top-N most similar products to a given product."""
        if not self.is_trained or product_id not in self.indices.index:
            return {}

        idx = self.indices[product_id]
        sim_scores = self.similarity_matrix[idx]

        scores = {}
        for i, score in enumerate(sim_scores):
            pid = self.products_df.iloc[i]['id']
            if pid != product_id and score > 0.01:
                scores[pid] = float(score)

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n])

    def get_user_content_scores(self, user_interactions, exclude_ids=None):
        """
        Given a dict of {product_id: interaction_weight}, compute content-based
        scores for all other products.
        """
        if not self.is_trained or not user_interactions:
            return {}

        exclude_ids = set(exclude_ids or [])
        scores = {}

        for product_id, weight in user_interactions.items():
            if product_id not in self.indices.index:
                continue
            idx = self.indices[product_id]
            sim_scores = self.similarity_matrix[idx]

            for i in range(len(sim_scores)):
                pid = self.products_df.iloc[i]['id']
                if pid not in exclude_ids and sim_scores[i] > 0.05:
                    scores[pid] = scores.get(pid, 0) + (sim_scores[i] * weight)

        return scores

    def save(self, path=None):
        """Save content model to disk and to the shared database."""
        os.makedirs(ML_MODELS_DIR, exist_ok=True)
        save_path = path or CONTENT_MODEL_PATH
        joblib.dump({
            'similarity_matrix': self.similarity_matrix,
            'products_df': self.products_df,
            'indices': self.indices,
        }, save_path)

        # Sync to shared database
        _save_model_to_db(save_path)

    def load(self, path=None):
        """Load content model from disk, falling back to database if local file is missing."""
        model_path = path or CONTENT_MODEL_PATH

        # If local file is missing, try downloading from database
        if not os.path.exists(model_path):
            logger.info("Local content model missing, trying database...")
            _load_model_from_db(model_path)

        if not os.path.exists(model_path):
            return False
        try:
            data = joblib.load(model_path)
            self.similarity_matrix = data['similarity_matrix']
            self.products_df = data['products_df']
            self.indices = data['indices']
            self.is_trained = True
            return True
        except Exception as e:
            logger.error("Failed to load content model: %s", e)
            return False


# ═══════════════════════════════════════════════════════════════════════════
# 2.5. ITEM-TO-ITEM COLLABORATIVE FILTERING (Amazon tarzi)
# ═══════════════════════════════════════════════════════════════════════════
class ItemItemCFModel:
    """
    Item-to-item collaborative filtering — Amazon'un "bunu alan sunu da aldi"
    algoritmasi.

    Her kullanicinin etkilesime girdigi urun "sepetini" (view + wishlist + review
    + purchase) toplar ve urun-urun benzerligini, kullanici-agirlik kolonlari
    uzerinden kosinus benzerligi ile hesaplar:

        sim(i, j) = (M[:,i] . M[:,j]) / (||M[:,i]|| * ||M[:,j]||)

    Bu yaklasim secildi cunku seyrek kataloglarda iyi calisir: her urun-cifti icin
    kaniti tum kullanicilar uzerinden toplar, tek bir kullaniciya bagli kalmaz.
    Content kulesinin (anlamsal benzerlik) yaninda davranissal sinyali getirir.
    """

    # Implicit sepet agirliklari: satin alma, bir urune bakmaktan cok daha guclu
    # bir birliktelik sinyalidir. View, view_count ile olcekli ama 5 ile sinirli.
    BASKET_WEIGHTS = {
        'purchase': 5.0,
        'wishlist': 3.0,
        'review': 2.0,
        'view': 1.0,
    }
    VIEW_COUNT_CAP = 5

    def __init__(self):
        self.sim_matrix = None      # np.ndarray (n_items x n_items), kosinus normalize
        self.item_ids = None        # list[int] — satir/sutun sirasi
        self.item_index = None      # dict {product_id: satir_idx}
        self.is_trained = False

    def _build_baskets(self, exclude_edges=None):
        """
        Her kullanicinin agirlikli urun sepetini tum implicit sinyallerden toplar.

        `exclude_edges`: leave-one-out degerlendirmesinde gizlenecek (user_id,
        product_id) ciftleri; verilirse o cift hicbir kullanicinin sepetine eklenmez.
        """
        from .models import ViewHistory, WishlistItem, Review, ProductOwnership

        exclude_edges = exclude_edges or set()
        baskets = {}  # {user_id: {product_id: agirlik}}

        def add(uid, pid, weight):
            if uid is None or pid is None:
                return
            if (uid, pid) in exclude_edges:
                return
            basket = baskets.setdefault(uid, {})
            basket[pid] = basket.get(pid, 0.0) + weight

        for v in ViewHistory.objects.values('customer_id', 'product_id', 'view_count'):
            capped = min(v['view_count'] or 1, self.VIEW_COUNT_CAP)
            add(v['customer_id'], v['product_id'], self.BASKET_WEIGHTS['view'] * capped)

        for w in WishlistItem.objects.filter(
            wishlist__customer__isnull=False
        ).values('wishlist__customer_id', 'product_id'):
            add(w['wishlist__customer_id'], w['product_id'], self.BASKET_WEIGHTS['wishlist'])

        for r in Review.objects.values('customer_id', 'product_id'):
            add(r['customer_id'], r['product_id'], self.BASKET_WEIGHTS['review'])

        for p in ProductOwnership.objects.values('customer_id', 'product_id'):
            add(p['customer_id'], p['product_id'], self.BASKET_WEIGHTS['purchase'])

        return baskets

    def train(self, verbose=True, exclude_edges=None):
        """
        Kullanici sepetlerinden urun-urun kosinus benzerlik matrisini kurar.

        `exclude_edges` leave-one-out degerlendirmesinde holdout kenarlarini gizler.
        """
        baskets = self._build_baskets(exclude_edges=exclude_edges)
        if not baskets:
            self.is_trained = False
            return False

        # Herhangi bir sepette gecen tum urunler evreni olusturur.
        item_set = set()
        for basket in baskets.values():
            item_set.update(basket.keys())

        self.item_ids = sorted(item_set)
        self.item_index = {pid: i for i, pid in enumerate(self.item_ids)}

        n_items = len(self.item_ids)
        user_ids = sorted(baskets.keys())
        n_users = len(user_ids)

        if n_items < 2:
            self.is_trained = False
            return False

        # Kullanici x urun agirlik matrisi; sutunlar arasi kosinus = item-item benzerlik.
        M = np.zeros((n_users, n_items), dtype=float)
        for u_idx, uid in enumerate(user_ids):
            for pid, weight in baskets[uid].items():
                M[u_idx, self.item_index[pid]] = weight

        self.sim_matrix = cosine_similarity(M.T)
        # Bir urun kendi komsusu degildir; kosegeni sifirla.
        np.fill_diagonal(self.sim_matrix, 0.0)
        self.is_trained = True

        if verbose:
            print(f"   Item-Item CF: {n_items} urun x {n_users} kullanici sepeti")

        return True

    def get_cooccurring(self, product_id, top_n=8, exclude_ids=None):
        """
        Verilen urunle davranissal olarak en cok birlikte gorulen urunleri dondurur.

        "Birlikte alinanlar" karuseli ve ana akistaki item-item bloku icin ortak
        giris noktasidir. [(product_id, benzerlik), ...] dondurur.
        """
        if not self.is_trained or product_id not in self.item_index:
            return []

        exclude = set(exclude_ids or [])
        exclude.add(product_id)

        idx = self.item_index[product_id]
        sims = self.sim_matrix[idx]
        order = np.argsort(sims)[::-1]

        out = []
        for j in order:
            sim = float(sims[j])
            if sim <= 0:
                break  # argsort azalan; ilk sifir/negatiften sonrasi da gereksiz.
            pid = self.item_ids[j]
            if pid in exclude:
                continue
            out.append((pid, sim))
            if len(out) >= top_n:
                break
        return out

    def get_user_itemcf_scores(self, user_interactions, exclude_ids=None):
        """
        Kullanicinin tum etkilesimlerinden item-item benzerligi toplayarak aday
        urun skorlari uretir.

            score(aday) = toplam_{tohum s} sim(s, aday) * agirlik_s

        Vektorize edildi: her tohum icin benzerlik satiri agirlikla carpilip
        bir akumulatorde toplanir; boylece N urun icin tek gecis yeter.
        """
        if not self.is_trained or not user_interactions:
            return {}

        exclude = set(exclude_ids or [])
        acc = np.zeros(len(self.item_ids), dtype=float)

        for seed_pid, weight in user_interactions.items():
            s_idx = self.item_index.get(seed_pid)
            if s_idx is None or weight <= 0:
                continue
            acc += self.sim_matrix[s_idx] * weight

        scores = {}
        for j, value in enumerate(acc):
            if value <= 0:
                continue
            pid = self.item_ids[j]
            if pid in exclude:
                continue
            scores[pid] = float(value)
        return scores

    def save(self, path=None):
        """Modeli diske ve paylasimli veritabanina kaydeder (duz numpy → guvenli pickle)."""
        os.makedirs(ML_MODELS_DIR, exist_ok=True)
        save_path = path or ITEMITEM_MODEL_PATH
        joblib.dump({
            'sim_matrix': self.sim_matrix,
            'item_ids': self.item_ids,
            'item_index': self.item_index,
        }, save_path)
        _save_model_to_db(save_path)

    def load(self, path=None):
        """Diskten (yoksa veritabanindan) yukler. Duz dizi oldugu icin surum-bagimsiz."""
        model_path = path or ITEMITEM_MODEL_PATH

        if not os.path.exists(model_path):
            logger.info("Local item-item model missing, trying database...")
            _load_model_from_db(model_path)

        if not os.path.exists(model_path):
            return False

        try:
            data = joblib.load(model_path)
            self.sim_matrix = data['sim_matrix']
            self.item_ids = data['item_ids']
            self.item_index = data['item_index']
            self.is_trained = (
                self.sim_matrix is not None
                and self.item_ids is not None
                and len(self.item_ids) > 1
            )
            return self.is_trained
        except Exception as e:
            logger.error("Failed to load item-item model: %s", e)
            return False


# ═══════════════════════════════════════════════════════════════════════════
# 3. HYBRID RECOMMENDER (Main Entry Point)
# ═══════════════════════════════════════════════════════════════════════════
class HybridRecommender:
    """
    Singleton hybrid recommender combining NCF + Content-Based + Popularity.

    Scoring formula per product:
      final_score = (α × ncf_score) + (β × content_score) + (γ × popularity_score)
                    + search_boost + price_sensitivity_boost
    
    Where α=0.5, β=0.3, γ=0.2 (learned/tunable weights).
    
    Cold-start handling:
      - New users (no interactions): popularity + content-based on categories
      - New products (no interactions): content-based only
    """

    _instance = None
    _lock = threading.Lock()

    # Hibrit kule agirliklari (varsayilan/bilgilendirme amacli — gercek agirliklar
    # _get_adaptive_weights ile kullanici seviyesine gore secilir). Dort kule:
    # Matrix Factorization (Netflix), Item-Item CF (Amazon), Content (Spotify), Popularity.
    WEIGHT_MF = 0.30
    WEIGHT_ITEM_ITEM = 0.30
    WEIGHT_CONTENT = 0.25
    WEIGHT_POPULARITY = 0.15
    # Geriye donuk uyumluluk: eski kod/test WEIGHT_NCF okuyabilir.
    WEIGHT_NCF = WEIGHT_MF

    # Yari omur degerleri etkilesim amacina gore ayarlanmistir:
    # Satin alma sinyali uzun sure gecerliligini korur, goruntulemeler daha hizli eskir.
    DECAY_PURCHASE_DAYS = 90
    DECAY_WISHLIST_DAYS = 45
    DECAY_REVIEW_DAYS = 60
    DECAY_VIEW_DAYS = 30
    DECAY_CLICK_DAYS = 45

    # Yeni eklenen stokta urunler, gecmis populerlik sinyalleri birikmeden
    # oneri listesine girebilsin diye gecici bir kesif boost'u alir.
    NEW_PRODUCT_MAX_AGE_DAYS = 30

    # Implicit negative sampling: kullanici son donemde bir urune bakmis ama
    # ne wishlist'e eklemis ne de satin almistir. Bu pasif gozlem zayif bir
    # negatif sinyaldir; recommender'in donup ayni urunu yeniden one cikarmasini
    # yumusatmak icin kucuk bir cezayla skoru azaltiriz.
    IMPLICIT_NEGATIVE_LOOKBACK_DAYS = 30
    IMPLICIT_NEGATIVE_PENALTY = 0.15

    # Time-of-day affinity: kullanicinin alistigi saat diliminde sik etkilesime
    # girdigi kategoriler ufak bir bonus alir. Bonus duzeyi bilincli olarak
    # dusuk tutulur cunku gercek niyet sinyallerini bastirmamasi gerekir.
    TIME_AFFINITY_BOOST = 0.10
    TIME_AFFINITY_TOP_CATEGORY_LIMIT = 2

    # Onboarding tercihleri: yeni kullanicinin secimleri birinci elde etkilesim
    # uretene kadar oneri listesini tamamen genel populer urunlerden korumak
    # icin kullanilir. Kullanicinin etkilesimi olgunlasinca bu boost devreden
    # cikarak gercek davranis sinyaline yer acar.
    ONBOARDING_BOOST = 0.15
    ONBOARDING_BOOST_MAX_INTERACTIONS = 5

    CACHE_TTL = getattr(settings, 'CACHE_TTL_LONG', 7200)

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init_models()
                    cls._instance = inst
        return cls._instance

    def _init_models(self):
        """Initialize sub-models, try to load, and auto-train in background if needed."""
        # Matrix Factorization kulesi. `self.ncf` adi geriye donuk uyumluluk icin
        # korunur (eski testler/komutlar bu attribute'u kullanir); `self.mf` ayni
        # nesneye okunabilir bir takma addir.
        self.ncf = NCFModel()
        self.mf = self.ncf
        # Item-Item CF kulesi (Amazon tarzi davranissal komsuluk).
        self.itemitem = ItemItemCFModel()
        self.content = ContentBasedModel()
        self._loaded = False
        self._training = False
        self._last_runtime_weights = {}

        # Try loading persisted models (checks local disk, then DB)
        ncf_loaded = self.ncf.load()
        itemitem_loaded = self.itemitem.load()
        content_loaded = self.content.load()
        self._loaded = ncf_loaded or itemitem_loaded or content_loaded

        if self._loaded:
            logger.info("Recommender loaded saved models from disk")
            if not getattr(settings, 'ML_DISABLE_BACKGROUND_JOBS', False):
                # Aktif kullanicilarin onerileri arka planda onceden uretilir;
                # test modunda arka plan DB yazimi beklenmediginden bu adim atlanir.
                self._pregenerate_in_background()
        else:
            logger.info("No saved models found; starting background training...")
            if not getattr(settings, 'ML_DISABLE_BACKGROUND_JOBS', False):
                self._train_in_background()

    def _pregenerate_in_background(self):
        """Pre-generate recommendations for active customers so pages load instantly."""
        import threading
        def _bg_pregen():
            try:
                from .models import Recommendation
                from django.contrib.auth import get_user_model
                User = get_user_model()
                # Only customers who don't already have recommendations
                customers = User.objects.filter(role='customer')
                for user in customers:
                    has_recs = Recommendation.objects.filter(customer=user).exists()
                    if not has_recs:
                        try:
                            recs = self.recommend(user, top_n=10, ignore_cache=True)
                            if recs:
                                for rec in recs:
                                    Recommendation.objects.create(
                                        customer=user,
                                        product_id=rec['product_id'],
                                        score=rec.get('score', 0),
                                        reason=rec.get('reason', 'AI önerisi')
                                    )
                                logger.info("📦 Pre-generated recs for user %s", user.id)
                        except Exception as e:
                            logger.debug("Pre-gen failed for user %s: %s", user.id, e)
                logger.info("Background pre-generation complete")
            except Exception as e:
                logger.warning("Background pre-generation failed: %s", e)
        t = threading.Thread(target=_bg_pregen, daemon=True)
        t.start()

    def _train_in_background(self):
        """Run training in a background thread so it never blocks requests."""
        if self._training:
            return
        self._training = True
        import threading
        def _bg_train():
            try:
                self.train(epochs=300, verbose=False)
                logger.info("Background training complete")
            except Exception as e:
                logger.warning("Background auto-train failed: %s", e)
            finally:
                self._training = False
        t = threading.Thread(target=_bg_train, daemon=True)
        t.start()

    def train(self, epochs=300, verbose=True):
        """Train all sub-models and persist them."""
        if verbose:
            print("=" * 60)
            print("BekoSIRS ML Recommendation System - Training Pipeline")
            print("=" * 60)

        start_time = time.time()

        # 1. Train content model (always works if products exist)
        content_ok = self.content.train(verbose=verbose)

        # 2. Train Matrix Factorization model (needs interaction data)
        mf_ok = self.ncf.train(epochs=epochs, verbose=verbose)

        # 3. Train Item-Item CF model (needs interaction data)
        itemitem_ok = self.itemitem.train(verbose=verbose)

        # 4. Siralama degerlendirmesi (R² yerine Recall@K/NDCG/MAP).
        #    Modeller egitildikten sonra holdout ile gercek oneri kalitesini olcer.
        if mf_ok or itemitem_ok or content_ok:
            try:
                ranking_metrics = self.evaluate_ranking(k=10)
                # MF metrik sozlugune sirali metrikleri ekle ki frontend/komutlar
                # tek yerden okuyabilsin.
                self.ncf.training_metrics.update(ranking_metrics)
            except Exception as e:
                logger.warning("Ranking evaluation failed: %s", e)

        # 5. Save models
        if content_ok:
            self.content.save()
        if mf_ok:
            self.ncf.save()
        if itemitem_ok:
            self.itemitem.save()

        elapsed = time.time() - start_time

        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Training complete in {elapsed:.1f}s")
            print(f"   Matrix Factorization: {'trained' if mf_ok else 'skipped (not enough data)'}")
            print(f"   Item-Item CF:         {'trained' if itemitem_ok else 'skipped (not enough data)'}")
            print(f"   Content model:        {'trained' if content_ok else 'skipped (no products)'}")
            print(f"   Models saved:         {ML_MODELS_DIR}")
            print(f"{'=' * 60}")

        self._loaded = content_ok or mf_ok or itemitem_ok
        return content_ok or mf_ok or itemitem_ok

    def recommend(self, user, top_n=10, ignore_cache=False, exclude_ids=None):
        """
        Kullanici icin hibrit oneri listesini uretir.

        Args:
            user: Oneri alinacak kullanici nesnesi.
            top_n: Donulecek en yuksek skorlu urun sayisi.
            ignore_cache: True ise etkilesim cache'i yeniden hesaplanir.
            exclude_ids: Listeye girmemesi gereken ek urun kimlikleri.

        Sahip olunan, dismiss edilen ve disaridan gelen exclude listeleri tek
        havuzda birlestirilir; bu yontem aday filtrelemeyi tek noktadan ve
        tutarli sekilde yonetmeyi kolaylastirir.
        """
        # Icerik modeli bellekte hazir degilse once egitiyoruz; boylece sistem
        # bos liste donmek yerine en azindan icerik tabanli aday uretebilir.
        if not self.content.is_trained:
            self.content.train(verbose=False)
            if self.content.is_trained:
                self.content.save()

        if self.content.products_df is None or self.content.products_df.empty:
            return []

        exclude_ids = set(exclude_ids or [])

        # Kullanici sinyalleri ve dislanacak urunler once tek yerde toplanir;
        # daha sonra her puan kaynagi ayni aday havuzu uzerinde calisir.
        user_interactions = self._get_user_interactions(user, ignore_cache)
        owned_product_ids = self._get_owned_product_ids(user)
        dismissed_product_ids = self._get_dismissed_product_ids(user)
        # Satin alinmis urunler tekrar onerilmez; bu akista "zaten sahip" bilgisi
        # kesin bir engel oldugu icin puan kirmak yerine dogrudan exclude edilir.
        exclude_ids.update(owned_product_ids)
        # Dismiss sinyali "bunu tekrar gosterme" anlamina gelir; bu nedenle
        # yumusak negatif skor yerine sert exclude olarak uygulanir.
        exclude_ids.update(dismissed_product_ids)

        # Adaptif agirliklar kullanicinin etkilesim derinligine gore secilir.
        # Soguk baslangicta populerlik daha guvenilirken aktif profilde NCF agir basar.
        weight_details = self._build_weight_details(user_interactions)
        self._last_runtime_weights[user.id] = weight_details

        final_scores = {}
        reasons = {}  # (kaynak_tipi, ek_bilgi) ikililerini saklar.
        # Her urun icin kule bazli katkilar; gerekce, blok sirasina gore degil EN COK
        # katki yapan kuleye gore atanir (asagida argmax ile). Boylece aktif kullanicida
        # her urun ayni "MF" etiketini almak yerine gercek baskin sinyali yansitir.
        contributions = {}

        all_product_ids = self.content.products_df['id'].tolist()

        # 1. Matrix Factorization (Netflix tarzi latent CF) skorlari
        # Yeterli etkilesimi olan kullanicida ana kisilestirme sinyali budur:
        # latent zevk vektoru, kullanicinin acikca gormedigi urunleri de tahmin eder.
        if self.ncf.is_trained:
            mf_scores = self.ncf.predict_for_user(
                user.id, all_product_ids, self.content.products_df
            )
            if mf_scores:
                max_mf = max(mf_scores.values()) or 1
                for pid, score in mf_scores.items():
                    if pid not in exclude_ids:
                        # Normalize edilen katki = (aday_skoru / en_yuksek_skor) * mf_agirligi.
                        # Farkli model olceklerini ayni 0-1 bandina getirir.
                        normalized = (score / max_mf) * weight_details['mf']
                        final_scores[pid] = final_scores.get(pid, 0) + normalized
                        contributions.setdefault(pid, {})['mf'] = normalized

        # 2. Item-Item CF (Amazon "bunu alanlar sunu da aldi") skorlari
        # Kullanicinin etkilesime girdigi urunlerin davranissal komsulari one cikar.
        if self.itemitem.is_trained and user_interactions:
            itemitem_scores = self.itemitem.get_user_itemcf_scores(
                user_interactions, exclude_ids
            )
            if itemitem_scores:
                max_ii = max(itemitem_scores.values()) or 1
                for pid, score in itemitem_scores.items():
                    if pid not in exclude_ids:
                        # Item-item katkisi da ayni olcege cekilir.
                        normalized = (score / max_ii) * weight_details['item_item']
                        final_scores[pid] = final_scores.get(pid, 0) + normalized
                        contributions.setdefault(pid, {})['item_item'] = normalized

        # 3. Icerik tabanli skorlar
        # Icerik tabanli skorlar benzer urun semantiklerini kullanarak ilgiyi genisletir.
        if self.content.is_trained and user_interactions:
            content_scores = self.content.get_user_content_scores(
                user_interactions, exclude_ids
            )
            if content_scores:
                max_content = max(content_scores.values()) or 1
                for pid, score in content_scores.items():
                    if pid not in exclude_ids:
                        # Icerik katkisi da ayni olcege cekilir.
                        # Ornek: 0.5 / 0.5 * 0.25 = 0.25. En iyi icerik adayi agirligin tamamini alir.
                        normalized = (score / max_content) * weight_details['content']
                        final_scores[pid] = final_scores.get(pid, 0) + normalized
                        contributions.setdefault(pid, {})['content'] = normalized

        # 4. Populerlik skorlari
        popularity_scores = self._get_popularity_scores()
        if popularity_scores:
            # Populerlik katmani soguk baslangicta emniyet agirligi olarak calisir.
            max_pop = max(popularity_scores.values()) or 1
            for pid, score in popularity_scores.items():
                if pid not in exclude_ids:
                    # Populerlik de 0-1 bandina cekilip agirlikla carpiliyor.
                    # Ornek: 12 / 15 * 0.8 = 0.64. Boylesi yeni kullanicida listeyi dengeler.
                    normalized = (score / max_pop) * weight_details['popularity']
                    final_scores[pid] = final_scores.get(pid, 0) + normalized
                    contributions.setdefault(pid, {})['popular'] = normalized

        # Gerekce atamasi: her urun icin EN COK katki yapan kule sebep olarak secilir.
        # Boost'lar (arama/fiyat/yeni/...) asagida kendi oncelik kurallariyla bu sebebi
        # gerektiginde gecersiz kilar.
        for pid, contrib in contributions.items():
            if contrib:
                best_source = max(contrib.items(), key=lambda kv: kv[1])[0]
                reasons[pid] = (best_source, None)

        # 5. Arama gecmisi bonusu
        search_boosts = self._get_search_boosts(user)
        # Arama terimleri acik niyet sinyali oldugu icin agirliklara dogrudan ek bonus veriyoruz.
        for pid, boost in search_boosts.items():
            if pid not in exclude_ids:
                final_scores[pid] = final_scores.get(pid, 0) + boost
                reasons[pid] = ('search', None)

        # 5. Fiyat duyarliligi bonusu
        price_boosts = self._get_price_sensitivity_boosts(user)
        for pid, boost in price_boosts.items():
            if pid not in exclude_ids and pid in final_scores:
                # Fiyat araligi uyumu yalnizca mevcut adaylara eklenir.
                # Ornek: mevcut skor 0.62 ise 0.1 bonus sonrasi 0.72 olur.
                final_scores[pid] += boost
                # Fiyat bir YEDEK gerekcedir: yalnizca daha guclu bir kisilestirme
                # sebebi (MF/item-item/content/search) yoksa etiketi yaz. Aksi halde
                # neredeyse tum adaylar fiyat araligina girdigi icin "butcenize uygun"
                # tum daha anlamli gerekceleri ezerdi.
                if boost > 0.1 and reasons.get(pid, (None,))[0] in (None, 'popular'):
                    reasons[pid] = ('price', None)

        # 6. Yeni urun kesif bonusu
        for pid, boost in self._get_new_product_boost().items():
            if pid not in exclude_ids:
                # Kucuk sabit bonus secildi; ornegin 0.4 ekleme yeni urunu gorunur
                # kilar ama halihazirda cok guclu bir adayi tamamen bastirmaz.
                final_scores[pid] = final_scores.get(pid, 0) + boost
                if boost > 0 and reasons.get(pid, (None,))[0] not in ('search', 'price'):
                    reasons[pid] = ('new', None)

        # 7. Onboarding kategori tercihleri (cold-start tohumu)
        # Sadece etkilesimi yetersiz kullanicilar icin uygulanir; aktif profilde
        # tercih sinyali davranis sinyalini bastirmasin diye otomatik kapanir.
        for pid, boost in self._get_onboarding_preference_boost(
            user, user_interactions=user_interactions,
        ).items():
            if pid not in exclude_ids:
                final_scores[pid] = final_scores.get(pid, 0) + boost
                if boost > 0 and reasons.get(pid, (None,))[0] in (None, 'popular'):
                    reasons[pid] = ('onboarding', None)

        # 8. Time-of-day affinity bonusu (gun dilimi aliskanligi)
        # Kucuk bonus secildi cunku amaci aliskanlik vurgulamak, gercek niyet
        # sinyallerini ezmemek.
        for pid, boost in self._get_time_affinity_boost(user).items():
            if pid not in exclude_ids:
                final_scores[pid] = final_scores.get(pid, 0) + boost
                # Tema sinyali zayif oldugu icin sebep etiketini sadece daha
                # spesifik bir sebep yoksa yaziyoruz.
                if boost > 0 and reasons.get(pid, (None,))[0] in (None, 'popular'):
                    reasons[pid] = ('time_affinity', None)

        # 9. Implicit negative sampling (zayif eksi sinyal)
        # Bakildi ama eylem alinmadi: skoru hafifce dusurerek ayni urunun
        # listede tekrar tekrar one cikmasini yumusatiyoruz. Tamamen exclude
        # etmemizin sebebi tek bakisla urunu mahkum etmemek.
        for pid, penalty in self._get_implicit_negative_signals(user).items():
            if pid in final_scores:
                final_scores[pid] += penalty

        # Sonucu bicimlendir ve dondur
        # Tum kaynaklardan gelen puanlar birlestirilir ve son sirali API cevabina cevrilir.
        return self._format_results(final_scores, reasons, top_n, exclude_ids, user=user)

    # -----------------------------------------------------------------------
    # Yardimci metodlar
    # -----------------------------------------------------------------------

    def _count_meaningful_interactions(self, user_interactions):
        """
        Kullanici seviyesini belirlemek icin pozitif etkilesimleri sayar.

        Sifir ve negatif degerleri bilerek dahil etmiyoruz; boylece dismiss gibi
        sinyaller soguk baslangic tespitini yapay olarak sisirmez.
        """
        return sum(1 for score in user_interactions.values() if score > 0)

    def _get_user_tier(self, user_interactions):
        """Etkilesim derinligini okunabilir bir oneri seviyesine cevirir."""
        interaction_count = self._count_meaningful_interactions(user_interactions)
        if interaction_count == 0:
            return 'cold_start'
        if interaction_count < 5:
            return 'light'
        if interaction_count < 20:
            return 'balanced'
        return 'active'

    def _get_adaptive_weights(self, user_interactions):
        """
        Kullanici etkilesim derinligine gore dort kule agirligini secer.

        Args:
            user_interactions: {product_id: skor} biciminde pozitif etkilesim haritasi.

        Returns:
            (mf, item_item, content, popularity) agirlik dortlusu — toplami 1.0.

        Mantik: soguk baslangicta CF kuleleri (MF + item-item) calisamaz cunku
        kullanicinin latent vektoru/sepeti yoktur; bu yuzden populerlik baskindir.
        Etkilesim biriktikce davranissal kuleler (MF, item-item) one cikar,
        populerlik emniyet agina geriler.
        """
        interaction_count = self._count_meaningful_interactions(user_interactions)

        # 0 etkilesim (cold_start): CF kuleleri sinyalsiz; populerlik %75 ile ana surucu.
        if interaction_count == 0:
            return (0.0, 0.0, 0.25, 0.75)
        # 1-4 etkilesim (light): ilk davranissal sinyaller gorunur ama populerlik hala onemli.
        if interaction_count < 5:
            return (0.10, 0.25, 0.30, 0.35)
        # 5-19 etkilesim (balanced): MF + item-item + content birlikte; dengeli faz.
        if interaction_count < 20:
            return (0.25, 0.30, 0.30, 0.15)
        # 20+ etkilesim (active): olgun profil; MF + item-item ana suruculer, populerlik geriler.
        return (0.35, 0.35, 0.25, 0.05)

    def _build_weight_details(self, user_interactions):
        """Tek kullanici icin API'ye hazir adaptif agirlik sozlugunu kurar."""
        mf_weight, item_item_weight, content_weight, popularity_weight = (
            self._get_adaptive_weights(user_interactions)
        )
        return {
            'mf': mf_weight,
            'item_item': item_item_weight,
            'content': content_weight,
            'popularity': popularity_weight,
            # Geriye donuk uyumluluk: eski kod/test 'ncf' anahtarini okuyabilir (= MF agirligi).
            'ncf': mf_weight,
            'user_tier': self._get_user_tier(user_interactions),
            'interaction_count': self._count_meaningful_interactions(user_interactions),
        }

    def get_runtime_weight_details(self, user, ignore_cache=False):
        """
        Verilen kullanici icin calisma anindaki adaptif agirliklari dondurur.

        View katmani cache'ten donse bile ayni helper'i cagirdiginda frontend,
        skorlama motorunun kullandigi agirliklarla birebir ayni payload'u alir.
        """
        cached_details = self._last_runtime_weights.get(user.id)
        if cached_details is not None and not ignore_cache:
            return cached_details

        user_interactions = self._get_user_interactions(user, ignore_cache=ignore_cache)
        weight_details = self._build_weight_details(user_interactions)
        self._last_runtime_weights[user.id] = weight_details
        return weight_details

    def _get_user_interactions(self, user, ignore_cache=False):
        """Kullanici etkilesim skorlarini {product_id: agirlik} biciminde toplar."""
        from .models import ProductOwnership, Review, WishlistItem, ViewHistory, Recommendation

        cache_key = f'ml_user_interactions_{user.id}'
        if not ignore_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        interactions = {}

        # Satin almalar kalici tercih sinyalidir; bu nedenle yari omurleri daha uzundur.
        for ownership in ProductOwnership.objects.filter(
            customer=user
        ).values('product_id', 'purchase_date'):
            decay = temporal_weight(
                ownership['purchase_date'],
                half_life_days=self.DECAY_PURCHASE_DAYS,
            )
            interactions[ownership['product_id']] = (
                interactions.get(ownership['product_id'], 0) + (5.0 * decay)
            )

        # Pozitif yorum acik memnuniyet bildirir; bu nedenle etkisi view'dan daha uzun surer.
        for r in Review.objects.filter(
            customer=user, rating__gt=3
        ).values('product_id', 'rating', 'created_at'):
            decay = temporal_weight(
                r['created_at'],
                half_life_days=self.DECAY_REVIEW_DAYS,
            )
            interactions[r['product_id']] = (
                interactions.get(r['product_id'], 0) + (float(r['rating']) * decay)
            )

        # Istek listesi satin alma kadar kalici degildir ama rastgele gezinmeden
        # daha guclu sinyal verir; bu yuzden orta seviye yari omur kullanilir.
        for item in WishlistItem.objects.filter(
            wishlist__customer=user
        ).values('product_id', 'added_at'):
            decay = temporal_weight(
                item['added_at'],
                half_life_days=self.DECAY_WISHLIST_DAYS,
            )
            interactions[item['product_id']] = (
                interactions.get(item['product_id'], 0) + (3.0 * decay)
            )

        # Goruntuleme kisa vadeli niyeti yansitir; bu nedenle en hizli bunlar curur.
        # view_count 15 ile sinirlanir ki tek sayfayi yenilemek tum siralamayi ezmesin.
        for vh in ViewHistory.objects.filter(customer=user).values('product_id', 'view_count', 'viewed_at'):
            weight = min(vh['view_count'], 15)
            decay = temporal_weight(
                vh['viewed_at'],
                half_life_days=self.DECAY_VIEW_DAYS,
            )
            interactions[vh['product_id']] = interactions.get(vh['product_id'], 0) + (weight * decay)

        # Tiklanan oneriler siradan view'dan daha gucludur cunku kullanici
        # kart uzerinden bilincli bir aksiyon almistir.
        for rec in Recommendation.objects.filter(
            customer=user, clicked=True
        ).values('product_id', 'created_at'):
            decay = temporal_weight(
                rec['created_at'],
                half_life_days=self.DECAY_CLICK_DAYS,
            )
            interactions[rec['product_id']] = interactions.get(rec['product_id'], 0) + (2.0 * decay)

        cache.set(cache_key, interactions, 300)
        return interactions

    def _get_owned_product_ids(self, user):
        """Kullanicinin zaten sahip oldugu urun kimliklerini dondurur."""
        from .models import ProductOwnership
        return set(
            ProductOwnership.objects.filter(
                customer=user
            ).values_list('product_id', flat=True)
        )

    def _get_dismissed_product_ids(self, user):
        """
        Kullanicinin acikca reddettigi oneri urun kimliklerini dondurur.

        Args:
            user: Dismiss tercihleri okunacak kullanici.

        Dismiss sinyali sert exclude kabul edilir cunku arayuzdeki anlami
        "bunu bir daha gosterme"dir; dusuk ilgi tahmini kadar yumusak degildir.
        """
        from .models import Recommendation

        return set(
            Recommendation.objects.filter(
                customer=user,
                dismissed=True,
            ).values_list('product_id', flat=True)
        )

    def _get_popularity_scores(self):
        """Calculate product popularity from aggregate interactions."""
        cache_key = 'ml_popularity_scores'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from .models import ViewHistory, Review, ProductOwnership
        from django.db.models import Count, Sum

        scores = {}

        # Count interactions per product
        view_counts = dict(
            ViewHistory.objects.values('product_id').annotate(
                total=Sum('view_count')
            ).values_list('product_id', 'total')
        )
        review_counts = dict(
            Review.objects.values('product_id').annotate(
                total=Count('id')
            ).values_list('product_id', 'total')
        )
        purchase_counts = dict(
            ProductOwnership.objects.values('product_id').annotate(
                total=Count('id')
            ).values_list('product_id', 'total')
        )

        # Weighted popularity
        all_pids = set(view_counts) | set(review_counts) | set(purchase_counts)
        for pid in all_pids:
            scores[pid] = (
                (view_counts.get(pid, 0) * 1.0) +
                (review_counts.get(pid, 0) * 3.0) +
                (purchase_counts.get(pid, 0) * 5.0)
            )

        cache.set(cache_key, scores, 1800)  # Cache for 30 min
        return scores

    def _get_new_product_boost(self):
        """
        Son donemde eklenen stoktaki urunler icin kisa omurlu bonus dondurur.

        Bu helper parametre almaz; dogrudan canli katalogdaki `created_at` ve
        stok bilgisini okur. Bu yontem secildi cunku populerlik odakli sistemler
        sifir etkilesimle baslayan yeni urunleri geri plana iter, burada ise
        sinirli bir kesif bonusu ile o bosluk kapatilir.
        """
        from .models import Product

        boosts = {}
        now = dt_datetime.now(dt_timezone.utc)

        # Yalnizca stokta olan ve son 30 gunde eklenen urunleri aliyoruz; stok
        # filtresi kullanicinin hemen satin alamayacagi urunleri one cikarmayi engeller.
        recent_products = Product.objects.filter(
            created_at__gte=now - timedelta(days=self.NEW_PRODUCT_MAX_AGE_DAYS),
            stock__gt=0,
        ).values('id', 'created_at')

        for product in recent_products:
            created_at = product['created_at']
            if created_at is None:
                continue

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=dt_timezone.utc)

            days_old = max(0, (now - created_at).days)
            # Kaba kovalar secildi cunku urun ekibine anlatmasi kolaydir:
            # 3 gunluk urun 0.4, 10 gunluk urun 0.25, 20 gunluk urun 0.1 bonus alir.
            if days_old <= 7:
                boosts[product['id']] = 0.4
            elif days_old <= 14:
                boosts[product['id']] = 0.25
            elif days_old <= self.NEW_PRODUCT_MAX_AGE_DAYS:
                boosts[product['id']] = 0.1

        return boosts

    def _get_search_boosts(self, user):
        """Boost products matching user's recent search terms."""
        from .models import SearchHistory

        if self.content.products_df is None or 'content' not in self.content.products_df.columns:
            return {}

        boosts = {}
        recent_searches = SearchHistory.objects.filter(
            customer=user
        ).order_by('-created_at')[:5]

        for search in recent_searches:
            term = search.query.lower()
            matches = self.content.products_df[
                self.content.products_df['content'].str.contains(term, na=False)
            ]
            for _, row in matches.iterrows():
                boosts[row['id']] = boosts.get(row['id'], 0) + 2.0

        return boosts

    def _get_price_sensitivity_boosts(self, user):
        """Boost products in the user's typical price range."""
        from .models import ProductOwnership, ViewHistory

        boosts = {}
        if self.content.products_df is None or 'price' not in self.content.products_df.columns:
            return boosts

        owned_prices = list(ProductOwnership.objects.filter(
            customer=user
        ).values_list('product__price', flat=True))
        viewed_prices = list(ViewHistory.objects.filter(
            customer=user
        ).values_list('product__price', flat=True)[:10])

        all_prices = [float(p) for p in owned_prices + viewed_prices if p]
        if not all_prices:
            return boosts

        avg_price = np.mean(all_prices)
        price_min = avg_price * 0.7
        price_max = avg_price * 1.3

        # Vectorized: build dict directly from filtered DataFrame columns
        df = self.content.products_df
        mask = (df['price'] >= price_min) & (df['price'] <= price_max)
        matched_ids = df.loc[mask, 'id'].values
        for pid in matched_ids:
            boosts[pid] = 0.5

        return boosts

    # -----------------------------------------------------------------------
    # Implicit negative sampling
    # -----------------------------------------------------------------------
    def _get_implicit_negative_signals(self, user):
        """
        Goruntulendi ama wishlist veya satin almaya donmemis urunler icin kucuk
        bir ceza haritasi dondurur.

        Args:
            user: Sinyaller hesaplanacak kullanici nesnesi.

        Returns:
            {product_id: -penalty} sozlugu. Pozitif aksiyona donen urunler
            cezadan muaf tutulur.

        Bu yontem secildi cunku tek bir tiklamayi sert bir negatif sinyale
        cevirmek riskli olur (tesaduf veya yanlis tiklama olabilir). Bunun
        yerine yalnizca son IMPLICIT_NEGATIVE_LOOKBACK_DAYS gun penceresindeki
        eylem disi goruntulemeler dusuk bir penalty olarak uygulanir.
        """
        from .models import ProductOwnership, ViewHistory, WishlistItem

        cutoff = dt_datetime.now(dt_timezone.utc) - timedelta(
            days=self.IMPLICIT_NEGATIVE_LOOKBACK_DAYS
        )

        viewed_pids = set(ViewHistory.objects.filter(
            customer=user,
            viewed_at__gte=cutoff,
        ).values_list('product_id', flat=True))

        if not viewed_pids:
            return {}

        # Sahip olunan ve wishlist'e eklenenler pozitif aksiyondur; bunlari
        # cezalandirmak yanlis sinyal uretir, bu nedenle setten cikariyoruz.
        positive_pids = set(ProductOwnership.objects.filter(
            customer=user,
            product_id__in=viewed_pids,
        ).values_list('product_id', flat=True))

        positive_pids.update(WishlistItem.objects.filter(
            wishlist__customer=user,
            product_id__in=viewed_pids,
        ).values_list('product_id', flat=True))

        ignored_pids = viewed_pids - positive_pids
        return {pid: -self.IMPLICIT_NEGATIVE_PENALTY for pid in ignored_pids}

    # -----------------------------------------------------------------------
    # Time-of-day affinity
    # -----------------------------------------------------------------------
    @staticmethod
    def _hour_bucket(hour):
        """
        24 saatlik bir zamani anlasilir bir gunduz dilimine cevirir.

        Sabah, ogleden sonra, aksam ve gece secimi urun ekibine acikca
        anlatilabilen ve kullanici aliskanliklarini yakalayan dort kovaya boler.
        """
        if 6 <= hour < 12:
            return 'morning'
        if 12 <= hour < 18:
            return 'afternoon'
        if 18 <= hour < 22:
            return 'evening'
        return 'night'

    def _get_time_affinity_boost(self, user, now=None):
        """
        Kullanicinin gunun ilgili diliminde sik gezdigi kategorilerde kucuk
        bir bonus uygular.

        Args:
            user: Bonus hesaplanacak kullanici.
            now: Test edilebilirlik icin opsiyonel zaman damgasi.

        Returns:
            {product_id: TIME_AFFINITY_BOOST} sozlugu.

        Bu sinyal aliskanlik temellidir; mesela aksam saatlerinde mutfak
        kategorilerine daha sik bakan biri icin aksam kosusunda mutfak
        urunleri kucuk bir bonus alir. Bonus duzeyi dusuk secildi cunku
        gercek ilgi sinyallerini ezecek kadar guclu olmamasi gerekir.
        """
        from .models import ViewHistory, Product

        reference_time = now or dt_datetime.now(dt_timezone.utc)
        current_bucket = self._hour_bucket(reference_time.hour)

        bucket_categories = {}
        view_history = ViewHistory.objects.filter(
            customer=user,
        ).select_related('product__category').values(
            'product__category_id', 'viewed_at', 'view_count',
        )

        for vh in view_history:
            cat_id = vh.get('product__category_id')
            viewed_at = vh.get('viewed_at')
            if cat_id is None or viewed_at is None:
                continue
            bucket = self._hour_bucket(viewed_at.hour)
            counts = bucket_categories.setdefault(bucket, {})
            counts[cat_id] = counts.get(cat_id, 0) + (vh.get('view_count') or 1)

        if current_bucket not in bucket_categories:
            return {}

        # Bu kovada en sik etkilesime giren ilk birkac kategori bonusu alir.
        # Daha fazlasi kullanicinin aliskanligindan ziyade gurultu olur.
        sorted_cats = sorted(
            bucket_categories[current_bucket].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        top_cat_ids = {cat_id for cat_id, _ in sorted_cats[: self.TIME_AFFINITY_TOP_CATEGORY_LIMIT]}

        if not top_cat_ids:
            return {}

        matched_ids = Product.objects.filter(
            category_id__in=top_cat_ids,
        ).values_list('id', flat=True)
        return {pid: self.TIME_AFFINITY_BOOST for pid in matched_ids}

    # -----------------------------------------------------------------------
    # Onboarding category preferences (cold-start seed)
    # -----------------------------------------------------------------------
    def _get_onboarding_preference_boost(self, user, user_interactions=None):
        """
        Onboarding sirasinda secilen kategorilerdeki urunlere kucuk bir bonus
        uygular.

        Args:
            user: Tercihleri okunacak kullanici.
            user_interactions: Onceden hesaplanmis etkilesim sozlugu (opsiyonel).

        Returns:
            {product_id: ONBOARDING_BOOST} sozlugu.

        Bonus yalnizca cold start ve light kullanicilar icin uygulanir; aktif
        kullanicilarda bu sinyal davranis sinyalini bastirmamali, dolayisiyla
        belirli bir etkilesim esiginden sonra otomatik olarak devre disi kalir.
        """
        from .models import UserCategoryPreference, Product

        if user_interactions is None:
            user_interactions = self._get_user_interactions(user)

        if (
            self._count_meaningful_interactions(user_interactions)
            >= self.ONBOARDING_BOOST_MAX_INTERACTIONS
        ):
            return {}

        preferred_cat_ids = list(UserCategoryPreference.objects.filter(
            customer=user,
        ).values_list('category_id', flat=True))

        if not preferred_cat_ids:
            return {}

        matched_ids = Product.objects.filter(
            category_id__in=preferred_cat_ids,
        ).values_list('id', flat=True)
        return {pid: self.ONBOARDING_BOOST for pid in matched_ids}

    # -----------------------------------------------------------------------
    # Bundle co-purchase recommendations
    # -----------------------------------------------------------------------
    def get_co_purchase_products(self, product_id, top_n=5, exclude_ids=None):
        """
        Verilen urunle birlikte sik satin alinan diger urunleri dondurur.

        Args:
            product_id: Demir koc urununun kimligi.
            top_n: Donulecek bundle uzunlugu.
            exclude_ids: Sonuctan haric tutulacak urun kimlikleri (opsiyonel).

        Returns:
            [{'product_id': int, 'co_purchase_count': int}, ...] listesi.

        Co-occurrence yontemi secildi cunku derin bir model gerektirmeden
        anlasilabilir bir esya esleme uretir; iki urunu ayni musteriler kac
        kez beraber satin almis bilgisi UI'ya rahatca seffaflastirilabilir.
        """
        from .models import ProductOwnership
        from collections import Counter

        exclude = set(exclude_ids or [])
        exclude.add(product_id)

        owner_ids = list(ProductOwnership.objects.filter(
            product_id=product_id,
        ).values_list('customer_id', flat=True))

        if not owner_ids:
            return []

        co_pids = ProductOwnership.objects.filter(
            customer_id__in=owner_ids,
        ).exclude(
            product_id__in=exclude,
        ).values_list('product_id', flat=True)

        counter = Counter(co_pids)
        return [
            {'product_id': pid, 'co_purchase_count': count}
            for pid, count in counter.most_common(top_n)
        ]

    def _normalize_metric_input(self, recommendation):
        """
        Oneri payload'unu metrik hesaplamaya uygun basit alanlara indirger.

        Recommendation ekrani bazen model nesnesi, bazen serilestirilmis sozluk
        alabilir. Bu helper iki bicimi de ayni yapida duzlestirerek cesitlilik ve
        kapsama hesaplarinin tek kod yolundan cikmasini saglar.
        """
        product_id = None
        category_name = None
        score_value = 0.0
        price_value = None

        if isinstance(recommendation, dict):
            product_data = recommendation.get('product') or {}
            category_data = product_data.get('category') or {}
            product_id = recommendation.get('product_id') or product_data.get('id')
            category_name = product_data.get('category_name') or category_data.get('name')
            score_value = recommendation.get('score', 0.0) or 0.0
            raw_price = product_data.get('price')
        else:
            product = getattr(recommendation, 'product', None)
            category = getattr(product, 'category', None)
            product_id = getattr(recommendation, 'product_id', None) or getattr(product, 'id', None)
            category_name = getattr(category, 'name', None)
            score_value = getattr(recommendation, 'score', 0.0) or 0.0
            raw_price = getattr(product, 'price', None)

        try:
            score_value = float(score_value)
        except (TypeError, ValueError):
            score_value = 0.0

        try:
            price_value = float(raw_price) if raw_price not in (None, '') else None
        except (TypeError, ValueError):
            price_value = None

        return {
            'product_id': product_id,
            'category_name': str(category_name).strip() if category_name else None,
            'score': score_value,
            'price': price_value,
        }

    def _compute_advanced_metrics(self, recommendations_list, all_products_count=None):
        """
        Calisma anindaki oneri listesi icin kalite metrikleri hesaplar.

        Args:
            recommendations_list: API'ye donulen sirali oneri listesi.
            all_products_count: Toplam katalog boyutu. Verilmezse veritabanindan okunur.

        Bu yontem secildi cunku cesitlilik ve kapsama gibi metrikler egitim
        verisinden degil, kullanicinin gercekte gordugu son listeden anlam kazanir.
        """
        normalized_items = [
            self._normalize_metric_input(recommendation)
            for recommendation in recommendations_list
        ]

        if all_products_count is None:
            from .models import Product

            # Katalog kapsamasini canli katalogla hesapliyoruz; sadece en son
            # model snapshot'ina bakmak is kurallarina gore eski sayi verebilir.
            all_products_count = Product.objects.count()
            if all_products_count == 0 and self.content.products_df is not None and not self.content.products_df.empty:
                all_products_count = len(self.content.products_df)

        categories = [
            item['category_name']
            for item in normalized_items
            if item['category_name']
        ]
        unique_categories = len(set(categories))
        # Cesitlilik = benzersiz kategori / liste uzunlugu.
        # Ornek: 2 kategori ve 4 urun varsa skor 0.5 olur.
        diversity_score = unique_categories / max(len(normalized_items), 1)

        unique_recommended = len({
            item['product_id']
            for item in normalized_items
            if item['product_id'] is not None
        })
        # Katalog kapsama = benzersiz onerilen urun / toplam katalog.
        # Ornek: 2 urun / 4 urun = 0.5 kapsama.
        catalog_coverage = unique_recommended / max(int(all_products_count or 0), 1)

        scores = [item['score'] for item in normalized_items]
        # Ortalama skor listenin genel gucunu ozetler.
        # Ornek: [0.9, 0.6] icin ortalama 0.75 olur.
        avg_recommendation_score = float(np.mean(scores)) if scores else 0.0

        prices = [item['price'] for item in normalized_items if item['price'] is not None]
        # Fiyat varyansi liste ici yayilimi olcer.
        # Ornek: [100, 200] icin varyans 2500 olur; daha yuksek deger farkli bantlari isaret eder.
        price_variance_in_list = float(np.var(prices)) if prices else 0.0

        return {
            'diversity_score': round(diversity_score, 3),
            'catalog_coverage': round(catalog_coverage, 3),
            'avg_recommendation_score': round(avg_recommendation_score, 3),
            'price_variance_in_list': round(price_variance_in_list, 3),
        }

    def get_advanced_metrics(self, recommendations_list, all_products_count=None):
        """Public wrapper so views can attach runtime list metrics to ml_metrics."""
        return self._compute_advanced_metrics(
            recommendations_list,
            all_products_count=all_products_count,
        )

    def _format_results(self, scores, reasons, top_n, exclude_ids, user=None):
        """Sort and format final recommendation results with category diversity."""
        from .models import Product, ViewHistory, Review, ProductOwnership, WishlistItem

        filtered = {
            pid: score for pid, score in scores.items()
            if pid not in exclude_ids and score > 0
        }
        # Sort ALL candidates by score
        sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

        # ── Get categories the user has actually interacted with ──
        user_categories = set()
        # Build a map of category -> most viewed product name (for rich reasons)
        category_top_product = {}  # {category_name: product_name}
        if user:
            # From views — get the most viewed product per category
            view_data = ViewHistory.objects.filter(
                customer=user
            ).select_related('product__category').order_by('-view_count')
            for vh in view_data:
                cat_name = vh.product.category.name if vh.product.category else None
                if cat_name:
                    cat_name = str(cat_name).strip()
                    user_categories.add(cat_name)
                    if cat_name not in category_top_product:
                        category_top_product[cat_name] = vh.product.name
            
            # From reviews
            review_cats = Review.objects.filter(
                customer=user
            ).values_list('product__category__name', flat=True).distinct()
            user_categories.update(str(c).strip() for c in review_cats if c)
            
            # From purchases
            purchase_cats = ProductOwnership.objects.filter(
                customer=user
            ).values_list('product__category__name', flat=True).distinct()
            user_categories.update(str(c).strip() for c in purchase_cats if c)
            
            # From wishlist
            wishlist_cats = WishlistItem.objects.filter(
                wishlist__customer=user
            ).values_list('product__category__name', flat=True).distinct()
            user_categories.update(str(c).strip() for c in wishlist_cats if c)

        def _build_reason(product, reason_tuple):
            """Build a specific, user-friendly reason string."""
            source = reason_tuple[0] if reason_tuple else 'default'
            cat_name = product.category.name if product.category else None
            
            # Find the user's top viewed product in this category
            top_viewed = category_top_product.get(cat_name) if cat_name else None
            
            if source == 'search':
                return f"Aramalarınıza göre önerildi"
            elif source == 'price':
                if cat_name:
                    return f"{cat_name} — bütçenize uygun"
                return "Fiyat aralığınıza uygun"
            elif source == 'content':
                if top_viewed:
                    # Truncate long product names
                    short_name = top_viewed[:30] + ('…' if len(top_viewed) > 30 else '')
                    return f"\"{short_name}\" incelemenize benzer"
                elif cat_name:
                    return f"{cat_name} ilgi alanınıza göre"
                return "Görüntüleme geçmişinize göre"
            elif source == 'item_item':
                # Amazon tarzi davranissal komsuluk: "bunu alanlar sunu da aldi".
                # Anchor urun, adayin KENDISI ise (kullanici onu cok gormus) dongusel
                # ifadeden kacinmak icin kategori temelli metne duseriz.
                if top_viewed and top_viewed != product.name:
                    short_name = top_viewed[:30] + ('…' if len(top_viewed) > 30 else '')
                    return f"\"{short_name}\" alanlar bunu da aldı"
                elif cat_name:
                    return f"{cat_name} alanlar bunu da tercih etti"
                return "Birlikte sık tercih edilenler"
            elif source in ('mf', 'ncf'):
                # Matrix Factorization: latent zevk benzerligi ("zevkinize gore").
                if top_viewed and top_viewed != product.name:
                    short_name = top_viewed[:30] + ('…' if len(top_viewed) > 30 else '')
                    return f"\"{short_name}\" beğenenler bunu da beğendi"
                elif cat_name:
                    return f"{cat_name} kategorisinde zevkinize göre seçildi"
                return "Zevkinize göre seçildi"
            elif source == 'popular':
                if cat_name:
                    return f"{cat_name} kategorisinde popüler"
                return "Çok tercih edilen ürün"
            elif source == 'new':
                if cat_name:
                    return f"Yeni eklenen {cat_name} ürünü"
                return "Yeni gelen ürün"
            elif source == 'onboarding':
                if cat_name:
                    return f"Sectiginiz {cat_name} kategorisinden"
                return "Tercih ettiginiz kategoriden"
            elif source == 'time_affinity':
                if cat_name:
                    return f"Bu saatte {cat_name} kategorisini sevdiniz"
                return "Bu saatte ilgilendiginiz urun"
            else:
                if cat_name:
                    return f"{cat_name} — sizin için seçildi"
                return "Sizin için seçildi"

        # ── Category diversity: max 4 items per category, only from user's categories ──
        MAX_PER_CATEGORY = 4
        category_counts = {}
        diverse_items = []
        added_pids = set()

        # Batch-fetch all candidate products in one query instead of N+1 individual lookups
        all_candidate_pids = [int(pid) for pid, _ in sorted_items]
        products_by_id = {
            p.id: p
            for p in Product.objects.select_related('category').filter(id__in=all_candidate_pids)
        }

        # Pass 1: Strict filtering based on user's known categories
        for pid, score in sorted_items:
            if len(diverse_items) >= top_n:
                break
            try:
                p_id = int(pid)
                product = products_by_id.get(p_id)
                if product is None:
                    continue
                cat_name = str(product.category.name).strip() if product.category else 'Other'

                # Skip categories the user has never interacted with (if we have user data)
                if user_categories and cat_name not in user_categories:
                    continue

                if category_counts.get(cat_name, 0) < MAX_PER_CATEGORY:
                    reason_tuple = reasons.get(pid, ('default', None))
                    diverse_items.append({
                        'product': product,
                        'product_id': p_id,
                        'score': round(float(score), 4),
                        'reason': _build_reason(product, reason_tuple),
                    })
                    category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
                    added_pids.add(p_id)
            except (ValueError, TypeError):
                continue

        # Pass 2: If we still don't have enough items, relax the category constraint
        if len(diverse_items) < top_n:
            for pid, score in sorted_items:
                if len(diverse_items) >= top_n:
                    break
                p_id = int(pid)
                if p_id in added_pids:
                    continue

                product = products_by_id.get(p_id)
                if product is None:
                    continue

                cat_name = str(product.category.name).strip() if product.category else 'Other'

                if category_counts.get(cat_name, 0) < MAX_PER_CATEGORY:
                    reason_tuple = reasons.get(pid, ('default', None))
                    diverse_items.append({
                        'product': product,
                        'product_id': p_id,
                        'score': round(float(score), 4),
                        'reason': _build_reason(product, reason_tuple),
                    })
                    category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
                    added_pids.add(p_id)

        # ── Format and return ──
        logger.info(
            "Recommending for user %s: %s candidates -> Filtered to %s",
            user.id if user else 'Guest',
            len(filtered),
            len(diverse_items),
        )
        
        if not diverse_items and sorted_items:
             logger.warning(
                 "All %s candidates were filtered out for user %s",
                 len(sorted_items),
                 user.id if user else 'Guest',
             )
             # Check one for debug
             pid, score = sorted_items[0]
             try:
                 p_id = int(pid)
                 p = Product.objects.get(id=p_id)
                 p_cat = str(p.category.name).strip() if p.category else 'Other'
                 logger.info(f"   Debug candidate 0: ID={p_id}, Name={p.name}, Cat={p_cat}, UserCats={user_categories}")
             except Exception as e: 
                 logger.error(f"   Debug failed: {e}")

        return diverse_items

    # -----------------------------------------------------------------------
    # Siralama degerlendirmesi (R² yerine gercek oneri kalitesi)
    # -----------------------------------------------------------------------
    def _score_all_items_for_eval(self, user, seed_interactions, mf_model, itemitem_model):
        """
        Degerlendirme icin verilen tohum etkilesimlerinden tum urunlere hibrit skor
        uretir. recommend()'in skorlama cekirdegini ozetler (boost'lar haric) ama
        hicbir urunu exclude etmez; boylece holdout urun de siralanabilir.

        MF ve item-item kuleleri DISARIDAN verilir cunku LOO sirasinda bunlar
        holdout kenarlari gizlenerek yeniden egitilmis gecici modellerdir; content
        ise yalnizca urun metnine baktigi icin sizinti uretmez ve self.content kullanilir.
        """
        w_mf, w_item_item, w_content, w_pop = self._get_adaptive_weights(seed_interactions)
        scores = {}

        def _blend(source_scores, weight):
            if not source_scores or weight <= 0:
                return
            max_v = max(source_scores.values()) or 1
            for pid, value in source_scores.items():
                scores[pid] = scores.get(pid, 0.0) + (value / max_v) * weight

        if mf_model is not None and mf_model.is_trained:
            _blend(mf_model.predict_for_user(user.id, None), w_mf)
        if itemitem_model is not None and itemitem_model.is_trained and seed_interactions:
            _blend(itemitem_model.get_user_itemcf_scores(seed_interactions), w_item_item)
        if self.content.is_trained and seed_interactions:
            _blend(self.content.get_user_content_scores(seed_interactions), w_content)
        _blend(self._get_popularity_scores(), w_pop)

        return scores

    def evaluate_ranking(self, k=10):
        """
        Gercek leave-one-out siralama degerlendirmesi.

        Her uygun kullanicinin en yeni pozitif etkilesimi (holdout) saklanir. Sizinti
        olmamasi icin TUM holdout kenarlari veriden gizlenip MF ve Item-Item modelleri
        GECICI olarak yeniden egitilir; ardindan her kullanici icin tum urunler
        siralanip holdout urunun top-K'ya girip girmedigine bakilir. Boylece model,
        tahmin ettigi urunu egitimde hic gormemis olur — metrik durust ve anlamlidir.

        R² (regresyon) yerine oneri sistemlerinde standart olan **Recall@K, NDCG@K ve
        MAP@K** dondurur (kullanici ortalamasi).

        Returns:
            {'eval_users', 'eval_k', 'recall_at_k', 'ndcg_at_k', 'map_at_k'} sozlugu.
        """
        from .models import ProductOwnership, WishlistItem, Review, ViewHistory

        # Kullanici basina (zaman_damgasi, product_id, agirlik) pozitif olaylari topla.
        events = {}  # {user_id: [(ts, pid, weight), ...]}

        def add_event(uid, ts, pid, weight):
            if uid is None or pid is None or ts is None:
                return
            events.setdefault(uid, []).append((ts, pid, weight))

        for p in ProductOwnership.objects.values('customer_id', 'product_id', 'purchase_date'):
            add_event(p['customer_id'], p['purchase_date'], p['product_id'], 5.0)
        for w in WishlistItem.objects.filter(
            wishlist__customer__isnull=False
        ).values('wishlist__customer_id', 'product_id', 'added_at'):
            add_event(w['wishlist__customer_id'], w['added_at'], w['product_id'], 3.0)
        for r in Review.objects.filter(rating__gt=3).values('customer_id', 'product_id', 'rating', 'created_at'):
            add_event(r['customer_id'], r['created_at'], r['product_id'], float(r['rating']))
        for v in ViewHistory.objects.values('customer_id', 'product_id', 'view_count', 'viewed_at'):
            add_event(v['customer_id'], v['viewed_at'], v['product_id'], min(v['view_count'] or 1, 5) * 1.0)

        # 1. Adim: her uygun kullanici icin holdout urunu ve tohum sinyallerini belirle.
        eval_plan = {}    # {uid: (holdout_pid, seed_dict)}
        exclude_edges = set()
        for uid, user_events in events.items():
            distinct_pids = {pid for _, pid, _ in user_events}
            if len(distinct_pids) < 2:
                continue  # holdout uretmek icin en az 2 farkli urun gerekir.

            # En yeni olay holdout. date/datetime karisik olabildigi icin str ile sirala.
            user_events_sorted = sorted(user_events, key=lambda e: str(e[0]))
            holdout_pid = user_events_sorted[-1][1]

            seed = {}
            for _, pid, weight in user_events_sorted[:-1]:
                if pid == holdout_pid:
                    continue
                seed[pid] = seed.get(pid, 0.0) + weight
            if not seed:
                continue

            eval_plan[uid] = (holdout_pid, seed)
            exclude_edges.add((uid, holdout_pid))

        if not eval_plan:
            return {
                'eval_users': 0,
                'eval_k': k,
                'recall_at_k': None,
                'ndcg_at_k': None,
                'map_at_k': None,
            }

        # 2. Adim: holdout kenarlari gizlenmis GECICI CF modelleri egit (sizinti yok).
        eval_mf = MatrixFactorizationModel()
        eval_mf.train(verbose=False, exclude_edges=exclude_edges)
        eval_itemitem = ItemItemCFModel()
        eval_itemitem.train(verbose=False, exclude_edges=exclude_edges)

        # 3. Adim: her kullanici icin sirala ve holdout'un top-K'da olup olmadigina bak.
        from django.contrib.auth import get_user_model
        User = get_user_model()

        recalls, ndcgs, average_precisions = [], [], []
        for uid, (holdout_pid, seed) in eval_plan.items():
            try:
                user = User.objects.get(id=uid)
            except User.DoesNotExist:
                continue

            scores = self._score_all_items_for_eval(user, seed, eval_mf, eval_itemitem)
            # Bilinen tohum urunleri siralamadan cikar; holdout aday olarak kalir.
            for pid in seed:
                scores.pop(pid, None)

            ranked = [pid for pid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]]

            if holdout_pid in ranked:
                rank = ranked.index(holdout_pid)  # 0-tabanli
                recalls.append(1.0)
                ndcgs.append(1.0 / math.log2(rank + 2))
                average_precisions.append(1.0 / (rank + 1))
            else:
                recalls.append(0.0)
                ndcgs.append(0.0)
                average_precisions.append(0.0)

        n = len(recalls)
        if n == 0:
            return {
                'eval_users': 0,
                'eval_k': k,
                'recall_at_k': None,
                'ndcg_at_k': None,
                'map_at_k': None,
            }

        return {
            'eval_users': n,
            'eval_k': k,
            'recall_at_k': round(sum(recalls) / n, 4),
            'ndcg_at_k': round(sum(ndcgs) / n, 4),
            'map_at_k': round(sum(average_precisions) / n, 4),
        }

    # -----------------------------------------------------------------------
    # Baseline karşılaştırması (ablation study)
    # -----------------------------------------------------------------------
    def evaluate_baselines(self, k=10):
        """
        Dört temel öneri stratejisini Recall@K, NDCG@K ve MAP@K üzerinden
        karşılaştırır (ablation study / baseline comparison).

        Baseline konfigürasyonları:
          - popularity_only : salt popülerlik sıralaması — kişiselleştirme yok
          - content_only    : yalnızca TF-IDF kosinüs benzerliği
          - mf_only         : yalnızca Matrix Factorization
          - hybrid_full     : dört kule tam ağırlıklarla (aktif kullanıcı profili)

        LOO protokolü evaluate_ranking() ile özdeştir. Fark: kule skorları
        kullanıcı başına bir kez hesaplanır (late-fusion), ardından tüm ağırlık
        senaryoları aynı ara vektörleri yeniden kullanır — böylece LOO modelleri
        sadece bir kez eğitilir.

        Referans: Cremonesi et al. (2010) "Performance of Recommender Algorithms
        on Top-N Recommendation Tasks", RecSys.

        Returns:
            {
              'eval_k': int,
              'eval_users': int,
              'baselines': {
                'popularity_only':  {'recall_at_k', 'ndcg_at_k', 'map_at_k', 'eval_users'},
                'content_only':     {...},
                'mf_only':          {...},
                'hybrid_full':      {...},
              }
            }
        """
        from .models import ProductOwnership, WishlistItem, Review, ViewHistory

        # ── 1. LOO eval planını kur (evaluate_ranking ile özdeş) ──
        events = {}

        def _add(uid, ts, pid, w):
            if uid is None or pid is None or ts is None:
                return
            events.setdefault(uid, []).append((ts, pid, w))

        for p in ProductOwnership.objects.values('customer_id', 'product_id', 'purchase_date'):
            _add(p['customer_id'], p['purchase_date'], p['product_id'], 5.0)
        for w in WishlistItem.objects.filter(
            wishlist__customer__isnull=False
        ).values('wishlist__customer_id', 'product_id', 'added_at'):
            _add(w['wishlist__customer_id'], w['added_at'], w['product_id'], 3.0)
        for r in Review.objects.filter(rating__gt=3).values(
            'customer_id', 'product_id', 'rating', 'created_at'
        ):
            _add(r['customer_id'], r['created_at'], r['product_id'], float(r['rating']))
        for v in ViewHistory.objects.values('customer_id', 'product_id', 'view_count', 'viewed_at'):
            _add(v['customer_id'], v['viewed_at'], v['product_id'], min(v['view_count'] or 1, 5) * 1.0)

        eval_plan = {}
        exclude_edges = set()
        for uid, user_events in events.items():
            distinct = {pid for _, pid, _ in user_events}
            if len(distinct) < 2:
                continue
            sorted_ev = sorted(user_events, key=lambda e: str(e[0]))
            holdout_pid = sorted_ev[-1][1]
            seed = {}
            for _, pid, weight in sorted_ev[:-1]:
                if pid != holdout_pid:
                    seed[pid] = seed.get(pid, 0.0) + weight
            if not seed:
                continue
            eval_plan[uid] = (holdout_pid, seed)
            exclude_edges.add((uid, holdout_pid))

        if not eval_plan:
            return {'eval_k': k, 'eval_users': 0, 'baselines': {}}

        # ── 2. Holdout sızıntısız geçici CF modelleri ──
        eval_mf = MatrixFactorizationModel()
        eval_mf.train(verbose=False, exclude_edges=exclude_edges)
        eval_ii = ItemItemCFModel()
        eval_ii.train(verbose=False, exclude_edges=exclude_edges)
        pop_scores = self._get_popularity_scores()

        # ── 3. Kullanıcı başına kule skorlarını bir kez hesapla ──
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # {uid: {'mf': {pid: s}, 'ii': {pid: s}, 'cb': {pid: s}, 'pop': {pid: s}}}
        tower_cache = {}
        for uid, (holdout_pid, seed) in eval_plan.items():
            try:
                user = User.objects.get(id=uid)
            except User.DoesNotExist:
                continue
            tower_cache[uid] = {
                'mf':  eval_mf.predict_for_user(user.id, None)  if eval_mf.is_trained  else {},
                'ii':  eval_ii.get_user_itemcf_scores(seed)      if eval_ii.is_trained   else {},
                'cb':  self.content.get_user_content_scores(seed) if self.content.is_trained else {},
                'pop': pop_scores,
            }

        # ── 4. Sabit ağırlıklarla skor karıştırma (late-fusion) ──
        def _blend_and_rank(towers, w_mf, w_ii, w_cb, w_pop, seed_pids):
            scores = {}

            def _add_tower(src, weight):
                if not src or weight <= 0:
                    return
                max_v = max(src.values()) or 1
                for pid, v in src.items():
                    scores[pid] = scores.get(pid, 0.0) + (v / max_v) * weight

            _add_tower(towers['mf'],  w_mf)
            _add_tower(towers['ii'],  w_ii)
            _add_tower(towers['cb'],  w_cb)
            _add_tower(towers['pop'], w_pop)
            for pid in seed_pids:
                scores.pop(pid, None)
            return [pid for pid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]

        # Aktif kullanıcı ağırlıkları: 20+ etkileşim profili
        ACTIVE_W = (0.35, 0.35, 0.25, 0.05)

        baseline_configs = {
            'popularity_only': (0.0,  0.0,  0.0,  1.0),
            'content_only':    (0.0,  0.0,  1.0,  0.0),
            'mf_only':         (1.0,  0.0,  0.0,  0.0),
            'hybrid_full':     ACTIVE_W,
        }

        results = {}
        for name, (w_mf, w_ii, w_cb, w_pop) in baseline_configs.items():
            recalls, ndcgs, aps = [], [], []
            for uid, (holdout_pid, seed) in eval_plan.items():
                if uid not in tower_cache:
                    continue
                ranked = _blend_and_rank(tower_cache[uid], w_mf, w_ii, w_cb, w_pop, set(seed))
                top_k = ranked[:k]
                if holdout_pid in top_k:
                    rank = top_k.index(holdout_pid)
                    recalls.append(1.0)
                    ndcgs.append(1.0 / math.log2(rank + 2))
                    aps.append(1.0 / (rank + 1))
                else:
                    recalls.append(0.0)
                    ndcgs.append(0.0)
                    aps.append(0.0)
            n = len(recalls)
            results[name] = {
                'recall_at_k': round(sum(recalls) / n, 4) if n else None,
                'ndcg_at_k':   round(sum(ndcgs)   / n, 4) if n else None,
                'map_at_k':    round(sum(aps)      / n, 4) if n else None,
                'eval_users':  n,
            }

        return {
            'eval_k':     k,
            'eval_users': len(tower_cache),
            'baselines':  results,
        }

    # -----------------------------------------------------------------------
    # Hibrit ağırlık optimizasyonu (grid search)
    # -----------------------------------------------------------------------
    def tune_hybrid_weights(self, k=10, step=0.15):
        """
        Grid search ile dört kule ağırlığını NDCG@K'yı maximize edecek şekilde
        optimize eder.

        Yöntem — "late-fusion grid search":
          1. LOO eval planı bir kez kurulur.
          2. Geçici CF modelleri holdout sızıntısız bir kez eğitilir.
          3. Her kullanıcı için dört kule skoru bir kez hesaplanır (ön-hesap).
          4. Ağırlık kombinasyonları üzerinde döngü: sadece skor karıştırma
             ve sıralama yapılır — model yeniden eğitimi yoktur.

        Bu "late-fusion" yaklaşımı, her kombinasyon için LOO'yu baştan
        çalıştırmaktan O(grid_size) kat daha hızlıdır.

        Referans: Adomavicius & Tuzhilin (2005) "Toward the Next Generation
        of Recommender Systems" (IEEE TKDE), Bölüm IV.C — hibrit ağırlık
        seçimi ve doğrulama.

        Args:
            k:    NDCG hesaplama derinliği.
            step: Izgara adım büyüklüğü (0.15 → ~30 geçerli kombinasyon).

        Returns:
            {
              'best_weights':       {'mf', 'item_item', 'content', 'popularity'},
              'best_ndcg_at_k':     float,
              'default_ndcg_at_k':  float,   # aktif kullanıcı varsayılan ağırlıkları
              'grid_size':          int,      # denenen toplam kombinasyon sayısı
              'eval_users':         int,
              'eval_k':             int,
            }
        """
        from .models import ProductOwnership, WishlistItem, Review, ViewHistory

        # ── 1. LOO eval planı ──
        events = {}

        def _add(uid, ts, pid, w):
            if uid is None or pid is None or ts is None:
                return
            events.setdefault(uid, []).append((ts, pid, w))

        for p in ProductOwnership.objects.values('customer_id', 'product_id', 'purchase_date'):
            _add(p['customer_id'], p['purchase_date'], p['product_id'], 5.0)
        for wl in WishlistItem.objects.filter(
            wishlist__customer__isnull=False
        ).values('wishlist__customer_id', 'product_id', 'added_at'):
            _add(wl['wishlist__customer_id'], wl['added_at'], wl['product_id'], 3.0)
        for r in Review.objects.filter(rating__gt=3).values(
            'customer_id', 'product_id', 'rating', 'created_at'
        ):
            _add(r['customer_id'], r['created_at'], r['product_id'], float(r['rating']))
        for v in ViewHistory.objects.values('customer_id', 'product_id', 'view_count', 'viewed_at'):
            _add(v['customer_id'], v['viewed_at'], v['product_id'], min(v['view_count'] or 1, 5) * 1.0)

        eval_plan = {}
        exclude_edges = set()
        for uid, user_events in events.items():
            distinct = {pid for _, pid, _ in user_events}
            if len(distinct) < 2:
                continue
            sorted_ev = sorted(user_events, key=lambda e: str(e[0]))
            holdout_pid = sorted_ev[-1][1]
            seed = {}
            for _, pid, weight in sorted_ev[:-1]:
                if pid != holdout_pid:
                    seed[pid] = seed.get(pid, 0.0) + weight
            if not seed:
                continue
            eval_plan[uid] = (holdout_pid, seed)
            exclude_edges.add((uid, holdout_pid))

        if not eval_plan:
            return {
                'best_weights': {'mf': 0.35, 'item_item': 0.35, 'content': 0.25, 'popularity': 0.05},
                'best_ndcg_at_k': None,
                'default_ndcg_at_k': None,
                'grid_size': 0,
                'eval_users': 0,
                'eval_k': k,
            }

        # ── 2. Geçici LOO modelleri ──
        eval_mf = MatrixFactorizationModel()
        eval_mf.train(verbose=False, exclude_edges=exclude_edges)
        eval_ii = ItemItemCFModel()
        eval_ii.train(verbose=False, exclude_edges=exclude_edges)
        pop_scores = self._get_popularity_scores()

        # ── 3. Kule skorlarını ön-hesapla ──
        from django.contrib.auth import get_user_model
        User = get_user_model()

        tower_cache = {}
        for uid, (_, seed) in eval_plan.items():
            try:
                user = User.objects.get(id=uid)
            except User.DoesNotExist:
                continue
            tower_cache[uid] = {
                'mf':  eval_mf.predict_for_user(user.id, None)   if eval_mf.is_trained   else {},
                'ii':  eval_ii.get_user_itemcf_scores(seed)       if eval_ii.is_trained    else {},
                'cb':  self.content.get_user_content_scores(seed)  if self.content.is_trained else {},
                'pop': pop_scores,
            }

        # ── 4. Late-fusion skor karıştırıcı ──
        def _ndcg_for_weights(w_mf, w_ii, w_cb, w_pop):
            ndcgs = []
            for uid, (holdout_pid, seed) in eval_plan.items():
                if uid not in tower_cache:
                    continue
                scores = {}

                def _blend(src, weight):
                    if not src or weight <= 0:
                        return
                    max_v = max(src.values()) or 1
                    for pid, v in src.items():
                        scores[pid] = scores.get(pid, 0.0) + (v / max_v) * weight

                _blend(tower_cache[uid]['mf'],  w_mf)
                _blend(tower_cache[uid]['ii'],  w_ii)
                _blend(tower_cache[uid]['cb'],  w_cb)
                _blend(tower_cache[uid]['pop'], w_pop)
                for pid in seed:
                    scores.pop(pid, None)
                ranked = [pid for pid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]]
                if holdout_pid in ranked:
                    ndcgs.append(1.0 / math.log2(ranked.index(holdout_pid) + 2))
                else:
                    ndcgs.append(0.0)
            return sum(ndcgs) / len(ndcgs) if ndcgs else 0.0

        # ── 5. Izgara arama — toplam 1.0'a normalleştirilen adımlar ──
        # Adım büyüklüğü (step) üçer ağırlık ekseni üzerinde döngü kurar;
        # dördüncü ağırlık (popularity) fark olarak hesaplanır.
        # Toplam negatif olan ve minimum popülerlik kısıtını aşan kombinasyonlar elenir.
        steps = [round(i * step, 2) for i in range(int(1.0 / step) + 1)]
        best_ndcg = -1.0
        best_combo = (0.35, 0.35, 0.25, 0.05)
        grid_size = 0

        for w_mf in steps:
            for w_ii in steps:
                for w_cb in steps:
                    w_pop = round(1.0 - w_mf - w_ii - w_cb, 4)
                    # Popülerlik ağırlığı negatif olamaz; min 0.05 ile cold-start güvencesi.
                    if w_pop < 0.05:
                        continue
                    grid_size += 1
                    ndcg = _ndcg_for_weights(w_mf, w_ii, w_cb, w_pop)
                    if ndcg > best_ndcg:
                        best_ndcg = ndcg
                        best_combo = (w_mf, w_ii, w_cb, w_pop)

        # Mevcut varsayılan aktif ağırlıkları için referans NDCG
        default_ndcg = _ndcg_for_weights(0.35, 0.35, 0.25, 0.05)

        logger.info(
            "tune_hybrid_weights: grid_size=%d, best=%s, NDCG@%d=%.4f (default=%.4f)",
            grid_size, best_combo, k, best_ndcg, default_ndcg,
        )

        return {
            'best_weights': {
                'mf':         best_combo[0],
                'item_item':  best_combo[1],
                'content':    best_combo[2],
                'popularity': best_combo[3],
            },
            'best_ndcg_at_k':    round(best_ndcg, 4),
            'default_ndcg_at_k': round(default_ndcg, 4),
            'grid_size':         grid_size,
            'eval_users':        len(tower_cache),
            'eval_k':            k,
        }

    def get_metrics(self):
        """
        Model durum ve kalite metriklerini döndürür.

        Üç katman:
          1. Eğitim metrikleri (offline, model kayıt edilirken hesaplanır):
             explained_variance, n_interactions, recall@K, NDCG@K, MAP@K
          2. Online metrikler (CTR / dismissal — gerçek kullanıcı davranışı):
             impressions, clicks, CTR, dismissals, dismissal_rate
             Referans: Hidasi et al. (2015) "Evaluating Recommender Systems"
             çalışmasında çevrimiçi CTR ölçümü temel online metrik olarak önerilir.
          3. Adaptif ağırlıklar (mevcut varsayılan değerler).
        """
        # ── Online metrikler: Recommendation tablosundan hesaplanır ──
        online_metrics = {}
        try:
            from .models import Recommendation
            from django.db.models import Count, Q

            agg = Recommendation.objects.aggregate(
                impressions=Count('id', filter=Q(is_shown=True)),
                clicks=Count('id', filter=Q(clicked=True)),
                dismissals=Count('id', filter=Q(dismissed=True)),
            )
            impressions = agg['impressions'] or 0
            clicks = agg['clicks'] or 0
            dismissals = agg['dismissals'] or 0
            online_metrics = {
                'impressions':    impressions,
                'clicks':         clicks,
                'dismissals':     dismissals,
                # CTR (Click-Through Rate): gösterilen önerilerden kaçı tıklandı.
                # Yüksek CTR kişiselleştirmenin işe yaradığını gösterir.
                'ctr':            round(clicks / impressions, 4) if impressions else None,
                # Dismissal rate: kullanıcının aktif olarak "ilgilenmiyorum" dediği oran.
                # Yüksek dismissal, model uyumsuzluğunun erken uyarı sinyalidir.
                'dismissal_rate': round(dismissals / impressions, 4) if impressions else None,
            }
        except Exception as e:
            logger.debug("Online metrik hesaplanamadı: %s", e)
            online_metrics = {'error': str(e)}

        return {
            # 'ncf' anahtari geriye donuk uyumluluk icin korunur; artik MF
            # (Matrix Factorization) modelinin egitim ve siralama metriklerini tasir.
            'ncf': self.ncf.training_metrics if self.ncf.is_trained else None,
            'mf': self.ncf.training_metrics if self.ncf.is_trained else None,
            'item_item': {
                'n_items': len(self.itemitem.item_ids) if self.itemitem.item_ids is not None else 0,
                'is_trained': self.itemitem.is_trained,
            },
            'content': {
                'n_products': len(self.content.products_df) if self.content.products_df is not None else 0,
                'is_trained': self.content.is_trained,
            },
            'models_loaded': self._loaded,
            'weights': {
                'mf': self.WEIGHT_MF,
                'item_item': self.WEIGHT_ITEM_ITEM,
                'content': self.WEIGHT_CONTENT,
                'popularity': self.WEIGHT_POPULARITY,
                'ncf': self.WEIGHT_MF,  # geriye donuk uyumluluk
            },
            'online_metrics': online_metrics,
        }

    def invalidate_cache(self):
        """Clear all cached data."""
        cache.delete('ml_popularity_scores')
        # Invalidate user-specific caches can't be done generically,
        # but they expire in 5 minutes anyway

    @classmethod
    def get_instance(cls):
        return cls()

    def _get_model_age_hours(self):
        """Return the age of the saved model in hours, or None if unknown."""
        if os.path.exists(METRICS_PATH):
            try:
                mtime = os.path.getmtime(METRICS_PATH)
                age_seconds = time.time() - mtime
                return age_seconds / 3600
            except OSError:
                pass
        return None

    def retrain_if_stale(self):
        """Retrain models if they are older than the configured interval."""
        retrain_interval = getattr(settings, 'ML_RETRAIN_INTERVAL_HOURS', 6)
        age_hours = self._get_model_age_hours()

        if age_hours is not None and age_hours < retrain_interval:
            logger.info(
                "ML model is %.1f hours old (threshold: %d hours) - skipping retrain",
                age_hours, retrain_interval
            )
            return False

        logger.info(
            "ML model is %s - starting retraining...",
            f"{age_hours:.1f} hours old" if age_hours is not None else "not found"
        )

        try:
            success = self.train(epochs=300, verbose=False)
            if success:
                logger.info("Periodic retraining complete")
                # Invalidate caches so new recommendations use fresh model
                self.invalidate_cache()
            else:
                logger.warning("Periodic retraining did not produce a model (insufficient data?)")
            return success
        except Exception as e:
            logger.error("Periodic retraining failed: %s", e)
            return False


# ═══════════════════════════════════════════════════════════════════════════
# Backward-compatible aliases
# ═══════════════════════════════════════════════════════════════════════════
ContentBasedRecommender = HybridRecommender


def get_recommender():
    """Factory function to get the singleton recommender instance."""
    return HybridRecommender.get_instance()
