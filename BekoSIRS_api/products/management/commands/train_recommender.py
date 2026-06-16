# products/management/commands/train_recommender.py
from django.conf import settings
from django.core.management.base import BaseCommand

from products.ml_recommender import get_recommender


class Command(BaseCommand):
    help = 'Train the ML recommendation model with current data'

    def add_arguments(self, parser):
        parser.add_argument("--epochs", type=int, default=300, help="Max training epochs (default 300)")

    def handle(self, *args, **options):
        """Run the recommender training pipeline and print a compact summary."""
        self.stdout.write(self.style.SUCCESS('Starting ML recommender training...'))

        previous_disable_jobs = getattr(settings, 'ML_DISABLE_BACKGROUND_JOBS', False)
        # Training should be deterministic and foreground-only; background refresh
        # threads can race with the command and add noisy side effects.
        settings.ML_DISABLE_BACKGROUND_JOBS = True

        try:
            recommender = get_recommender()
            success = recommender.train(epochs=options["epochs"], verbose=True)

            if success:
                self.stdout.write(self.style.SUCCESS('\nModel trained successfully'))
                metrics = recommender.get_metrics()

                content = metrics.get('content', {})
                if content.get('is_trained'):
                    self.stdout.write(
                        f"  - Content model trained with {content.get('n_products', 0)} products"
                    )
                else:
                    self.stdout.write(self.style.WARNING("  - Content model skipped or failed"))

                # 'ncf' anahtarı geriye dönük uyumluluk için korunur; artık MF metriklerini taşır.
                mf = metrics.get('mf') or metrics.get('ncf')
                if mf:
                    self.stdout.write(f"  - MF Algorithm:         {mf.get('algorithm', 'TruncatedSVD')}")
                    self.stdout.write(f"  - MF Latent Components: {mf.get('n_components')}")
                    self.stdout.write(f"  - MF Explained Var.:    {mf.get('explained_variance')}")
                    self.stdout.write(f"  - Recall@K:             {mf.get('recall_at_k')}")
                    self.stdout.write(f"  - NDCG@K:               {mf.get('ndcg_at_k')}")
                    self.stdout.write(f"  - MAP@K:                {mf.get('map_at_k')}")
                    self.stdout.write(f"  - Eval Users:           {mf.get('eval_users')}")
                    self.stdout.write(f"  - n_interactions:       {mf.get('n_interactions')}")
                    self.stdout.write(f"  - Trained at:           {mf.get('trained_at')}")
                else:
                    self.stdout.write(
                        self.style.WARNING("  - MF model skipped (insufficient interaction data)")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '\nTraining did not complete successfully (possibly not enough data).'
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Training failed: {str(e)}'))
            raise
        finally:
            settings.ML_DISABLE_BACKGROUND_JOBS = previous_disable_jobs
