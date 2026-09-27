from decimal import Decimal

from django.core.management.base import BaseCommand

from books.models import Book


class Command(BaseCommand):
    help = "Crea El Quijote como ejemplo si su ISBN todavía no existe."

    def handle(self, *args, **options):
        isbn = "9788437604947"
        book = Book.objects.filter(isbn=isbn).first()
        if book is None:
            book = Book(
                title="El Quijote",
                author="Miguel de Cervantes",
                isbn=isbn,
                cost_usd=Decimal("15.99"),
                stock_quantity=25,
                category="Literatura Clásica",
                supplier_country="ES",
            )
            book.full_clean()
            book.save()
            self.stdout.write(self.style.SUCCESS(f"Creado: {book.title} (id={book.pk})."))
        else:
            self.stdout.write(f"Ya existe: {book.title} (id={book.pk}). No se modificó.")
