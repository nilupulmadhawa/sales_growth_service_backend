# management/commands/import_csv.py
import csv
from django.core.management.base import BaseCommand
from prediction.models import MultiCategoryDataset

class Command(BaseCommand):
    help = 'Import data from CSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                MultiCategoryDataset.objects.create(
                    event_time=row['event_time'],
                    event_type=row['event_type'],
                    product_id=row['product_id'],
                    category_id=row['category_id'],
                    category_code=row['category_code'],
                    brand=row['brand'],
                    price=row['price'],
                    user_id=row['user_id'],
                    user_session=row['user_session'],
                    age=row['age'],
                    gender=row['gender'],
                    location=row['location']
                )

        self.stdout.write(self.style.SUCCESS('Data imported successfully'))
