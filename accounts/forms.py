from django import forms


class EmailForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@company.com", "autofocus": True})
    )


class OTPForm(forms.Form):
    code = forms.CharField(
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={"placeholder": "6-digit code", "inputmode": "numeric", "autocomplete": "one-time-code", "autofocus": True}
        ),
    )
