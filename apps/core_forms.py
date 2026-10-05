"""Utilitários compartilhados de formulário."""
from django import forms


class EstiloBootstrapMixin:
    """Aplica as classes do Bootstrap e atributos de acessibilidade aos campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)) and not isinstance(
                widget, forms.CheckboxSelectMultiple
            ):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                css = ""
            else:
                css = "form-control"
            if css:
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
            if campo.required:
                widget.attrs.setdefault("aria-required", "true")
            if campo.help_text:
                widget.attrs["aria-describedby"] = f"{self._id_campo(nome)}_ajuda"

    def _id_campo(self, nome):
        auto_id = self.auto_id if isinstance(self.auto_id, str) and "%s" in self.auto_id else "id_%s"
        return auto_id % self.add_prefix(nome)

    def full_clean(self):
        super().full_clean()
        # Marca os campos inválidos para leitores de tela e para o estilo do Bootstrap
        for nome in self.errors:
            if nome in self.fields:
                w = self.fields[nome].widget
                w.attrs["aria-invalid"] = "true"
                ids = [i for i in w.attrs.get("aria-describedby", "").split() if i]
                ids.insert(0, f"{self._id_campo(nome)}_erro")
                w.attrs["aria-describedby"] = " ".join(dict.fromkeys(ids))
                w.attrs["class"] = f"{w.attrs.get('class', '')} is-invalid".strip()
