class PrivateAPIResponses:
    """Evitar almacenar respuestas de cuentas/inventario en clientes o proxies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.split("/", 2)[1] in {"auth", "users", "books", "rates"}:
            response["Cache-Control"] = "no-store"
        return response
