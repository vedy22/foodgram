from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

User = get_user_model()


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор рецепта",
        null=False,
    )
    name = models.CharField(
        verbose_name="Название рецепта",
        max_length=200,
        db_index=True,
        null=False,
    )
    image = models.ImageField(
        verbose_name="Изображение рецепта",
        upload_to="backend_media",
        null=False,
    )
    text = models.TextField(verbose_name="Описание", null=False)
    ingredients = models.ManyToManyField(
        to="Ingredient",
        through="RecipeIngredient",
        verbose_name="Список ингредиентов",
        related_name="recipes",
    )
    tags = models.ManyToManyField(
        to="Tag",
        verbose_name="Теги",
        related_name="recipe",
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name="Время приготовления в минутах.",
        null=False,
        validators=(MinValueValidator(1),),
    )
    pub_date = models.DateTimeField(
        verbose_name="Дата публикации",
        default=timezone.now,
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ("-pub_date",)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        verbose_name="Название тега", max_length=200, unique=True
    )
    color = models.CharField(
        verbose_name="Цвет",
        max_length=7,
        help_text=("Цвет в должен быть в формате HEX, например: #49B64E."),
        validators=(
            RegexValidator(
                regex=r"^#[a-fA-F0-9]{6}$",
                message="Цвет должен быть в формате HEX.",
                code="wrong_hex_code",
            ),
        ),
    )
    slug = models.SlugField(
        verbose_name="URL метка", help_text="Введите slug тега", unique=True
    )

    class Meta:
        verbose_name = "Tег"
        verbose_name_plural = "Tеги"
        ordering = ("-pk",)
        constraints = [
            models.UniqueConstraint(
                fields=("name", "slug"), name="unique_name_slug"
            )
        ]

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name="Название ингредиента",
        max_length=200,
        null=False,
        db_index=True,
    )
    measurement_unit = models.CharField(
        verbose_name="Еденица измерения",
        max_length=200,
        null=False,
    )

    class Meta:
        verbose_name = "ингредиент"
        verbose_name_plural = "ингредиенты"
        ordering = ("-pk",)
        constraints = [
            models.UniqueConstraint(
                fields=("name", "measurement_unit"), name="unique_name_unit"
            )
        ]

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name="Ингредиент",
        on_delete=models.CASCADE,
        related_name="ingredient_recipes",
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Количество",
        validators=(MinValueValidator(1),),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient_pair",
            )
        ]


class FavouriteRecipe(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="favourite",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
        related_name="favourite",
    )
    date_added: models.DateTimeField = models.DateTimeField(
        verbose_name="дата создания", auto_now_add=True
    )

    class Meta:
        verbose_name = "Избранное"
        ordering = ("-date_added",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_favourite"
            )
        ]

    def __str__(self):
        return (f"{self.user.username} добавил "
                f"{self.recipe.name} в избранное.")


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Рецепт",
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Список покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_shopping_cart"
            )
        ]

    def __str__(self):
        return (f"{self.user.username} добавил "
                f"{self.recipe.name} в список покупок.")
