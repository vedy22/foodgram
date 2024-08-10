

class IsAuthAndExistsMixin:
    def is_auth_and_exists(self, obj, model):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return model.objects.filter(recipe=obj, user=request.user).exists()
        return False
