# core/signals.py
import os
from io import BytesIO
from pdf2image import convert_from_path
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image
from .models import ProjectProgress


@receiver(post_save, sender=ProjectProgress)
def generate_pdf_thumbnail(sender, instance, created, **kwargs):
    """Automatically create a thumbnail for the uploaded PDF"""
    if created and instance.file.name.lower().endswith(".pdf"):
        try:
            pdf_path = instance.file.path
            pages = convert_from_path(pdf_path, dpi=100, first_page=1, last_page=1)
            if not pages:
                return

            img_io = BytesIO()
            pages[0].save(img_io, format="JPEG", quality=80)
            img_content = ContentFile(img_io.getvalue())

            base_name = os.path.basename(instance.file.name).replace(".pdf", ".jpg")
            instance.thumbnail.save(base_name, img_content, save=True)
        except Exception as e:
            print(f"Error generating thumbnail for {instance.file.name}: {e}")
