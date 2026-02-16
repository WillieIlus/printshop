# subscriptions/mpesa_services.py

import requests
import base64
import re
from datetime import datetime
from django.conf import settings
from decimal import Decimal


def normalize_phone(phone: str) -> str:
    """Normalize Kenyan phone to 254XXXXXXXXX for Daraja."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0"):
        digits = "254" + digits[1:]
    elif not digits.startswith("254"):
        digits = "254" + digits
    return digits[:12]


class MPesaStkPushService:
    """
    M-Pesa STK Push (C2B) - customer pays via phone prompt.
    Used for subscription upgrades.
    """

    def __init__(self):
        self.consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "") or ""
        self.consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "") or ""
        self.shortcode = getattr(settings, "MPESA_SHORTCODE", "") or ""
        self.passkey = getattr(settings, "MPESA_PASSKEY", "") or ""
        self.base_url = getattr(
            settings, "MPESA_BASE_URL", "https://sandbox.safaricom.co.ke"
        )
        self.callback_url = getattr(
            settings, "MPESA_STK_CALLBACK_URL",
            "https://yourdomain.com/api/payments/mpesa/callback/"
        )

    def get_access_token(self):
        """Get OAuth access token from M-Pesa."""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        if "error" in data:
            raise ValueError(data.get("error_description", str(data)))
        return data.get("access_token")

    def initiate_stk_push(self, phone: str, amount: Decimal, account_ref: str) -> dict:
        """
        Initiate STK push. Returns Daraja response with CheckoutRequestID.
        """
        token = self.get_access_token()
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": normalize_phone(phone),
            "PartyB": self.shortcode,
            "PhoneNumber": normalize_phone(phone),
            "CallBackURL": self.callback_url,
            "AccountReference": account_ref[:12],
            "TransactionDesc": "PrintShop subscription",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return response.json()


class MPesaB2BService:
    """
    Basic M-Pesa B2B integration for subscription payments.
    This is a simplified version - expand based on your needs.
    """
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.initiator_name = settings.MPESA_INITIATOR_NAME
        self.security_credential = settings.MPESA_SECURITY_CREDENTIAL
        
        self.base_url = "https://sandbox.safaricom.co.ke"  # Change to live URL in production
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa."""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded}"
        }
        
        response = requests.get(url, headers=headers)
        return response.json().get("access_token")
    
    def initiate_b2b_payment(self, subscription, amount):
        """
        Initiate a B2B payment request.
        In real implementation, this would be triggered by a billing cron job.
        """
        token = self.get_access_token()
        
        url = f"{self.base_url}/mpesa/b2b/v1/paymentrequest"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "Initiator": self.initiator_name,
            "SecurityCredential": self.security_credential,
            "CommandID": "BusinessPayBill",
            "SenderIdentifierType": "4",
            "RecieverIdentifierType": "4",
            "Amount": str(amount),
            "PartyA": self.shortcode,
            "PartyB": subscription.mpesa_shortcode,
            "AccountReference": subscription.mpesa_account_reference,
            "Remarks": f"Subscription payment for {subscription.shop.name}",
            "QueueTimeOutURL": settings.MPESA_TIMEOUT_URL,
            "ResultURL": settings.MPESA_RESULT_URL,
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()