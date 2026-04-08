"""
Temporal decay tests for the hybrid recommender interaction pipeline.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from products.ml_recommender import HybridRecommender, temporal_weight
from products.models import Category, Product, ProductOwnership, Review, ViewHistory, Wishlist, WishlistItem

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_ml_cache():
    """Clear recommender cache so each test evaluates fresh interaction weights."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def customer(db):
    """Create a customer user for recommender interaction tests."""
    return User.objects.create_user(username='decay-user', password='Decay123!', role='customer')


@pytest.fixture
def category(db):
    """Create a shared category so products are easy to compare in tests."""
    return Category.objects.create(name='Temporal Decay Category')


@pytest.fixture
def products(db, category):
    """Create a pair of products used to compare old and recent interactions."""
    recent_product = Product.objects.create(
        name='Yeni İlgi Ürünü',
        brand='Beko',
        category=category,
        price=Decimal('12000.00'),
        stock=5,
    )
    old_product = Product.objects.create(
        name='Eski İlgi Ürünü',
        brand='Beko',
        category=category,
        price=Decimal('11000.00'),
        stock=5,
    )
    return recent_product, old_product


def _build_recommender_for_unit_test():
    """Create a lightweight recommender instance without triggering singleton side effects."""
    return object.__new__(HybridRecommender)


def test_temporal_weight_recent_interaction_higher():
    """Güncel etkileşim eski etkileşimden daha yüksek ağırlık almalı."""
    recent = temporal_weight(datetime.now(timezone.utc) - timedelta(days=5))
    old = temporal_weight(datetime.now(timezone.utc) - timedelta(days=60))
    assert recent > old


def test_temporal_weight_half_life():
    """30 günde ağırlık yarıya düşmeli (±%5 tolerans)."""
    weight = temporal_weight(
        datetime.now(timezone.utc) - timedelta(days=30),
        half_life_days=30,
    )
    assert abs(weight - 0.5) < 0.05


@pytest.mark.django_db
def test_interactions_include_decay(customer, products):
    """_get_user_interactions eski view kaydını yeni kayıttan daha düşük ağırlıkta toplamalı."""
    recent_product, old_product = products
    recommender = _build_recommender_for_unit_test()

    recent_view = ViewHistory.objects.create(
        customer=customer,
        product=recent_product,
        view_count=8,
    )
    old_view = ViewHistory.objects.create(
        customer=customer,
        product=old_product,
        view_count=8,
    )

    # Auto timestamp alanlarını tarihsel senaryolara çekiyoruz çünkü gerçek
    # üretim verisinde kararlar bu alanların yaşına göre veriliyor.
    ViewHistory.objects.filter(pk=recent_view.pk).update(
        viewed_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    ViewHistory.objects.filter(pk=old_view.pk).update(
        viewed_at=datetime.now(timezone.utc) - timedelta(days=90)
    )

    interactions = recommender._get_user_interactions(customer, ignore_cache=True)

    expected_recent = 8 * temporal_weight(
        datetime.now(timezone.utc) - timedelta(days=2),
        half_life_days=HybridRecommender.DECAY_VIEW_DAYS,
    )
    expected_old = 8 * temporal_weight(
        datetime.now(timezone.utc) - timedelta(days=90),
        half_life_days=HybridRecommender.DECAY_VIEW_DAYS,
    )

    assert interactions[recent_product.id] > interactions[old_product.id]
    assert interactions[recent_product.id] == pytest.approx(expected_recent, rel=0.05)
    assert interactions[old_product.id] == pytest.approx(expected_old, rel=0.05)


@pytest.mark.django_db
def test_purchase_decay_uses_date_field(customer, category):
    """DateField purchase_date kayıtları da decay formülüne göre ağırlıklandırılmalı."""
    owned_product = Product.objects.create(
        name='Satın Alınan Ürün',
        brand='Beko',
        category=category,
        price=Decimal('18000.00'),
        stock=3,
    )
    ProductOwnership.objects.create(
        customer=customer,
        product=owned_product,
        purchase_date=date.today() - timedelta(days=90),
    )

    recommender = _build_recommender_for_unit_test()
    interactions = recommender._get_user_interactions(customer, ignore_cache=True)

    expected_weight = 5.0 * temporal_weight(
        date.today() - timedelta(days=90),
        half_life_days=HybridRecommender.DECAY_PURCHASE_DAYS,
    )
    assert interactions[owned_product.id] == pytest.approx(expected_weight, rel=0.05)


@pytest.mark.django_db
def test_wishlist_and_review_decay_are_applied(customer, products):
    """Wishlist ve review sinyalleri kendi half-life değerleriyle ölçeklenmeli."""
    wishlist_product, review_product = products
    wishlist = Wishlist.objects.create(customer=customer)

    wishlist_item = WishlistItem.objects.create(
        wishlist=wishlist,
        product=wishlist_product,
    )
    review = Review.objects.create(
        customer=customer,
        product=review_product,
        rating=5,
        comment='Harika',
    )

    WishlistItem.objects.filter(pk=wishlist_item.pk).update(
        added_at=datetime.now(timezone.utc) - timedelta(days=45)
    )
    Review.objects.filter(pk=review.pk).update(
        created_at=datetime.now(timezone.utc) - timedelta(days=60)
    )

    recommender = _build_recommender_for_unit_test()
    interactions = recommender._get_user_interactions(customer, ignore_cache=True)

    expected_wishlist = 3.0 * temporal_weight(
        datetime.now(timezone.utc) - timedelta(days=45),
        half_life_days=HybridRecommender.DECAY_WISHLIST_DAYS,
    )
    expected_review = 5.0 * temporal_weight(
        datetime.now(timezone.utc) - timedelta(days=60),
        half_life_days=HybridRecommender.DECAY_REVIEW_DAYS,
    )

    assert interactions[wishlist_product.id] == pytest.approx(expected_wishlist, rel=0.05)
    assert interactions[review_product.id] == pytest.approx(expected_review, rel=0.05)
