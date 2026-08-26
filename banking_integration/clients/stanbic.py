# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

import frappe
import requests

from frappe import _


class StanbicClient:
    """
    Client for Stanbic Connect API.

    Uses the shared Bank Integration Credentials DocType.

    Responsibilities:
        - OAuth authentication
        - Token caching
        - Authenticated HTTP requests
        - Exposing Stanbic API endpoints
    """

    AUTH_PATH = "/api/sandbox/auth/oauth2/token"

    # ------------------------------------------------------------------
    # PAYMENT ENDPOINTS
    # ------------------------------------------------------------------

    EFT_PATH = "/api/sandbox/eft-payments/"
    MOBILE_PAYMENT_PATH = "/api/sandbox/mobile-payments/"
    MPESA_CHECKOUT_PATH = "/api/sandbox/mpesa-checkout/"
    PESALINK_PATH = "/api/sandbox/pesalink-payments/"
    RTGS_PATH = "/api/sandbox/rtgs-payments/"
    STANBIC_PAYMENT_PATH = "/api/sandbox/stanbic-payments/"

    # ------------------------------------------------------------------
    # ACCOUNT / INFORMATION ENDPOINTS
    # ------------------------------------------------------------------

    SORT_CODES_PATH = "/api/sandbox/fetch-sortcodes/"
    STATEMENTS_PATH = "/api/sandbox/fetchStatements/"
    TRANSACTIONS_PATH = "/api/sandbox/fetchTransactions/"
    ZOHO_STATEMENTS_PATH = "/api/sandbox/statements/"

    # ------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------

    def __init__(self, credentials):
        self.credentials = credentials

        if credentials.environment == "Sandbox":
            self.base_url = (
                credentials.sandbox_url
                or "https://sandbox.connect.stanbicbank.co.ke"
            ).rstrip("/")

        else:
            self.base_url = (
                credentials.production_url
                or ""
            ).rstrip("/")

        if not self.base_url:
            frappe.throw(
                "Stanbic credentials: No API URL configured."
            )

    # ==================================================================
    # AUTHENTICATION
    # ==================================================================

    def get_access_token(self, force_refresh=False):
        """
        Return a valid Stanbic OAuth access token.

        Reuses the stored token where possible and requests
        a new token when expired or force_refresh=True.
        """

        now = frappe.utils.now_datetime()

        if (
            not force_refresh
            and self.credentials.access_token
            and self.credentials.token_expiry
            and self.credentials.token_expiry > now
        ):
            return self.credentials.access_token

        client_id = self.credentials.client_id

        client_secret = self.credentials.get_password(
            "client_secret"
        )

        if not client_id:
            frappe.throw(
                "Stanbic Client ID is missing."
            )

        if not client_secret:
            frappe.throw(
                "Stanbic Client Secret is missing."
            )

        token_url = (
            f"{self.base_url}"
            "/api/sandbox/auth/oauth2/token"
        )

        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "payments",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                token_url,
                data=payload,
                headers=headers,
                timeout=30,
            )

        except requests.exceptions.RequestException as e:
            frappe.log_error(
                title="Stanbic OAuth Request Error",
                message=str(e),
            )

            frappe.throw(
                f"Failed to connect to Stanbic: {str(e)}"
            )

        if response.status_code != 200:
            frappe.log_error(
                title="Stanbic OAuth Error",
                message=(
                    f"URL: {token_url}\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text}"
                ),
            )

            frappe.throw(
                _(
                    "Stanbic authentication failed: "
                    "HTTP {0}. Check Error Log for details."
                ).format(
                    response.status_code
                )
            )

        try:
            data = response.json()

        except ValueError:
            frappe.throw(
                "Stanbic authentication returned invalid JSON."
            )

        access_token = data.get("access_token")

        if not access_token:
            frappe.throw(
                f"Stanbic did not return an access token: {data}"
            )

        expires_in = int(
            data.get(
                "expires_in",
                3600,
            )
        )

        self.credentials.access_token = access_token

        self.credentials.token_expiry = (
            frappe.utils.add_to_date(
                now,
                seconds=max(
                    expires_in - 60,
                    60,
                ),
                as_datetime=True,
            )
        )

        self.credentials.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        return access_token
    
    # ==================================================================
    # GENERIC REQUEST
    # ==================================================================

    def request(
        self,
        method,
        endpoint,
        payload=None,
        retry_on_401=True,
    ):
        """
        Make an authenticated Stanbic API request.

        Returns:

        {
            "status_code": 200,
            "data": {...},
            "success": True
        }
        """

        token = self.get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        response = requests.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        # --------------------------------------------------------------
        # Retry once if the token was rejected
        # --------------------------------------------------------------

        if (
            response.status_code == 401
            and retry_on_401
        ):

            token = self.get_access_token(
                force_refresh=True
            )

            headers["Authorization"] = (
                f"Bearer {token}"
            )

            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

        # --------------------------------------------------------------
        # Parse response
        # --------------------------------------------------------------

        try:
            data = response.json()

        except ValueError:
            data = {
                "raw_text": response.text
            }

        return {
            "status_code": response.status_code,
            "data": data,
            "success": response.status_code in (
                200,
                201,
                202,
            ),
        }

    # ==================================================================
    # BASIC HTTP METHODS
    # ==================================================================

    def get(self, endpoint):
        return self.request(
            "GET",
            endpoint,
        )

    def post(
        self,
        endpoint,
        payload,
    ):
        return self.request(
            "POST",
            endpoint,
            payload=payload,
        )

    # ==================================================================
    # PAYMENTS
    # ==================================================================

    def eft_payment(self, payload):
        """
        Bank Transfer via EFT.
        """

        return self.post(
            self.EFT_PATH,
            payload,
        )

    def mobile_payment(self, payload):
        """
        Mobile Money B2C payment.
        """

        return self.post(
            self.MOBILE_PAYMENT_PATH,
            payload,
        )

    def mpesa_checkout(self, payload):
        """
        STK Push / M-PESA Checkout.
        """

        return self.post(
            self.MPESA_CHECKOUT_PATH,
            payload,
        )

    def pesalink_payment(self, payload):
        """
        Inter-bank transfer via Pesalink.
        """

        return self.post(
            self.PESALINK_PATH,
            payload,
        )

    def rtgs_payment(self, payload):
        """
        Inter-bank transfer via RTGS.
        """

        return self.post(
            self.RTGS_PATH,
            payload,
        )

    def stanbic_payment(self, payload):
        """
        Payment to another Stanbic account.
        """

        return self.post(
            self.STANBIC_PAYMENT_PATH,
            payload,
        )

    # ==================================================================
    # ACCOUNT INFORMATION
    # ==================================================================

    def fetch_sort_codes(self, payload):
        """
        Fetch Stanbic / beneficiary bank sort codes.
        """

        return self.post(
            self.SORT_CODES_PATH,
            payload,
        )

    def fetch_statements(self, payload):
        """
        Fetch account transaction history.
        """

        return self.post(
            self.STATEMENTS_PATH,
            payload,
        )

    def fetch_transactions(self, payload):
        """
        Fetch account mini statement / last 20 transactions.
        """

        return self.post(
            self.TRANSACTIONS_PATH,
            payload,
        )

    def fetch_zoho_statements(self, payload):
        """
        Fetch transaction history through the ZohoBooks
        statements endpoint.
        """

        return self.post(
            self.ZOHO_STATEMENTS_PATH,
            payload,
        )