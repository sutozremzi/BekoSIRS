# products/management/commands/build_recommender.py
from django.core.management.base import BaseCommand
from products.models import CustomUser
from products.ml_recommender import HybridRecommender

class Command(BaseCommand):
    help = 'Runs the Hybrid ML Recommender'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, nargs='?', default=1)

    def handle(self, *args, **options):
        user_id = options['user_id']
        
        self.stdout.write("Initializing Hybrid ML Engine...")
        recommender = HybridRecommender()
        self.stdout.write("Training Complete.")

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {user_id} not found."))
            return

        self.stdout.write(f"\n--- Generating Recommendations for {user.username} ---")
        recommendations = recommender.recommend(user, top_n=5)

        if recommendations:
            for i, item in enumerate(recommendations, 1):
                p = item['product']
                score = item['score']
                self.stdout.write(self.style.SUCCESS(f"{i}. {p.name} (Score: {score:.2f})"))
                self.stdout.write(f"   Brand: {p.brand} | Cat: {p.category.name if p.category else 'None'}")
        else:
            self.stdout.write(self.style.WARNING("No recommendations found."))