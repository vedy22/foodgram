from rest_framework.pagination import PageNumberPagination
import os
from dotenv import load_dotenv

load_dotenv()


class CustomPagination(PageNumberPagination):
    """Переопределение названия поля,
    отвечающего за количество результатов в выдаче."""

    PAGE_SIZE = os.getenv('PAGE_SIZE')
    PAGE_SIZE_QUERY_PARAM = os.getenv('PAGE_SIZE_QUERY_PARAM')
