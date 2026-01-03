# travel/forms.py
from django import forms
from django.contrib.auth import authenticate
from .models import CustomUser,Trip,TripItinerary,ChecklistItem,GroupMember

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = CustomUser
        # We only ask for these fields. Username is generated automatically.
        fields = ['first_name', 'last_name', 'email', 'country', 'state']

    # 1. Ensure Email is Unique
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered. Please log in.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # Auto-generate username from First Name
        first_name = self.cleaned_data.get('first_name', '').strip().lower()
        if not first_name:
            first_name = "user"
            
        base_username = first_name.replace(" ", "")
        username = base_username
        counter = 1
        
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        user.username = username

        if commit:
            user.save()
        return user

# 2. Custom Email Login Form
class UserLoginForm(forms.Form):
    email = forms.EmailField(label="Email Address", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'name@company.com'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            # Find the user with this email
            try:
                user_obj = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise forms.ValidationError("This email is not registered.")
            except CustomUser.MultipleObjectsReturned:
                raise forms.ValidationError("Multiple accounts found with this email.")

            # Authenticate using the found username and provided password
            user = authenticate(username=user_obj.username, password=password)
            
            if user is None:
                raise forms.ValidationError("Invalid password. Please try again.")
            
            self.user_cache = user
        
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)
    
class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['name', 'destination', 'start_date', 'end_date', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Summer Vacation'}),
            
            # MAKE SURE THIS IS TextInput (Not Select)
            'destination': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_destination', 'placeholder': 'Start typing a city...', 'autocomplete': 'off'}),
            
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
class ItineraryForm(forms.ModelForm):
    class Meta:
        model = TripItinerary
        fields = ['location', 'date', 'notes']
        widgets = {
            'location': forms.TextInput(attrs={
                'class': 'form-control', 
                'id': 'id_stop_location', # Unique ID for API script
                'placeholder': 'Enter City/Stop...'
            }),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Activities planned...'}),
        }
        
class ChecklistForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ['item_name', 'priority']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Passport, Charger...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
        
class GroupMemberForm(forms.ModelForm):
    class Meta:
        model = GroupMember
        fields = ['name', 'contact']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email (Optional)'}),
        }