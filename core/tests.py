from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import MerchantProfile, Order, Product
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
class ProductModelTests(TestCase):
    def test_merchant_product_availability(self):
        u=get_user_model().objects.create_user(username="shop",password="test-password-123",role="merchant")
        m=MerchantProfile.objects.create(user=u,shop_name="Demo Market")
        p=Product.objects.create(merchant=m,name="Water",price=Decimal("2.50"))
        self.assertTrue(p.available)

class CentralAccountSubscriptionTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.admin = get_user_model().objects.create_user(
            username="platform-admin", password="admin-password-123", role="admin"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_creates_identity_based_customer_account(self):
        response = self.client.post("/api/admin/users/", {
            "identity_number": "987654321", "first_name": "Demo", "last_name": "Customer",
            "phone": "0590000000", "role": "customer"
        }, format="json")
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(identity_number="987654321")
        self.assertEqual(user.username, "987654321")
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.check_password(response.data["temporary_password"]))

    def test_admin_sets_individual_subscription(self):
        user = get_user_model().objects.create_user(
            username="captain-id", password="temporary-password", role="captain", subscription_required=True
        )
        response = self.client.post(f"/api/admin/users/{user.id}/subscription/", {
            "amount": "35.00", "months": 2, "starts_on": timezone.localdate().isoformat(), "status": "active"
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["amount"], "35.00")
        self.assertEqual(response.data["total_due"], "70.00")

    def test_admin_subscription_ledger_and_status_change(self):
        from .models import Subscription
        user = get_user_model().objects.create_user(
            username="ledger-captain", password="captain-password-123", role="captain", subscription_required=True
        )
        today = timezone.localdate()
        sub = Subscription.objects.create(
            user=user, amount=Decimal("40.00"), months=1, starts_on=today,
            ends_on=today + timedelta(days=30), status="active"
        )
        response = self.client.get("/api/admin/subscriptions/")
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data if item["id"] == sub.id)
        self.assertTrue(row["is_current"])
        self.assertEqual(row["user_id"], user.id)
        changed = self.client.patch(f"/api/admin/subscriptions/{sub.id}/", {"status": "pending"}, format="json")
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(changed.data["subscription_active"])

    def test_public_registration_cannot_create_privileged_roles(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/auth/register/", {
            "username": "open-merchant", "password": "long-password", "first_name": "Open",
            "phone": "0590000001", "role": "merchant", "shop_name": "Unapproved store"
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username="open-merchant").exists())

    def test_public_registration_creates_customers(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/auth/register/", {
            "username": "open-customer", "password": "long-password", "first_name": "Open",
            "phone": "0590000002", "role": "customer"
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["role"], "customer")

    def test_merchant_preparation_time_rejects_unsupported_value(self):
        from rest_framework.test import APIClient
        merchant_user = get_user_model().objects.create_user(
            username="prep-merchant", password="merchant-password-123", role="merchant"
        )
        customer = get_user_model().objects.create_user(
            username="prep-customer", password="customer-password-123", role="customer"
        )
        store = MerchantProfile.objects.create(user=merchant_user, shop_name="Prep Market")
        order = Order.objects.create(customer=customer, merchant=store, order_type="store", status="new")
        client = APIClient()
        client.force_authenticate(merchant_user)
        response = client.post(f"/api/orders/{order.id}/accept/", {"prep_minutes": 35}, format="json")
        self.assertEqual(response.status_code, 400)

class RideRequestTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.customer = get_user_model().objects.create_user(
            username="ride-customer", password="customer-password-123", role="customer"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_customer_can_create_ride_with_coordinates(self):
        from unittest.mock import patch
        route = {"available": True, "distance_meters": 2300, "duration_seconds": 420,
                 "geometry": [[35.2137, 31.7683], [35.22, 31.78]], "source": "road_network"}
        with patch("core.views.road_route", return_value=route):
            response = self.client.post("/api/orders/ride/", {
                "pickup_address": "Pickup point", "dropoff_address": "Destination",
                "pickup_latitude": 31.7683, "pickup_longitude": 35.2137,
                "dropoff_latitude": 31.7800, "dropoff_longitude": 35.2200,
                "requires_checkpoint": True
            }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["order_type"], "ride")
        self.assertEqual(response.data["status"], "new")
        self.assertEqual(response.data["checkpoint_fee"], "15.00")
        self.assertEqual(response.data["distance_km"], "2.30")
        self.assertEqual(response.data["estimated_duration_minutes"], 7)
        self.assertEqual(response.data["distance_source"], "road_network")
        self.assertGreater(float(response.data["total"]), 15)

    def test_ride_requires_both_coordinate_pairs(self):
        response = self.client.post("/api/orders/ride/", {
            "pickup_address": "Pickup point", "dropoff_address": "Destination"
        }, format="json")
        self.assertEqual(response.status_code, 400)

class CaptainStatusConsistencyTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from .models import CaptainProfile, Subscription
        self.User = get_user_model()
        self.admin = self.User.objects.create_user(
            username="status-admin", password="admin-password-123", role="admin"
        )
        self.captain = self.User.objects.create_user(
            username="yusuf-test", password="captain-password-123", role="captain",
            subscription_required=True,
        )
        self.profile = CaptainProfile.objects.create(
            user=self.captain, approved=True, online=False, vehicle_type="motorcycle"
        )
        today = timezone.localdate()
        Subscription.objects.create(
            user=self.captain, amount=Decimal("35.00"), months=1,
            starts_on=today, ends_on=today + timedelta(days=30), status="active",
        )
        self.client = APIClient()

    def test_admin_and_captain_both_report_missing_subscription_as_inactive(self):
        from .models import Subscription
        Subscription.objects.filter(user=self.captain).delete()
        self.client.force_authenticate(self.captain)
        captain_response = self.client.get("/api/captains/me/")
        self.assertEqual(captain_response.status_code, 200)
        self.assertFalse(captain_response.data["subscription_active"])
        self.client.force_authenticate(self.admin)
        admin_response = self.client.get("/api/admin/operations/")
        row = next(x for x in admin_response.data["captains"] if x["user_id"] == self.captain.id)
        self.assertFalse(row["subscription_active"])

    def test_captain_api_and_admin_report_same_approved_subscription_state(self):
        self.client.force_authenticate(self.captain)
        captain_response = self.client.get("/api/captains/me/")
        self.assertEqual(captain_response.status_code, 200)
        self.assertTrue(captain_response.data["approved"])
        self.assertTrue(captain_response.data["subscription_active"])
        self.assertEqual(captain_response.data["user_id"], self.captain.id)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.get("/api/admin/operations/")
        self.assertEqual(admin_response.status_code, 200)
        row = next(x for x in admin_response.data["captains"] if x["id"] == self.profile.id)
        self.assertEqual(row["user_id"], self.captain.id)
        self.assertTrue(row["approved"])
        self.assertTrue(row["subscription_active"])


class CashSettlementAccountingTests(TestCase):
    def test_captain_collects_full_total_and_commission_is_snapshotted(self):
        from rest_framework.test import APIClient
        from .models import CaptainProfile, CashSettlement
        merchant_user = get_user_model().objects.create_user(username="cash-shop", password="shop-password-123", role="merchant")
        captain_user = get_user_model().objects.create_user(username="cash-captain", password="captain-password-123", role="captain")
        customer = get_user_model().objects.create_user(username="cash-customer", password="customer-password-123", role="customer")
        merchant = MerchantProfile.objects.create(user=merchant_user, shop_name="Cash Shop", commission_type="percent", commission_value=Decimal("10.00"))
        captain = CaptainProfile.objects.create(user=captain_user)
        order = Order.objects.create(
            customer=customer, merchant=merchant, captain=captain, order_type="store",
            status="assigned", payment_method="cash", subtotal=Decimal("100.00"),
            delivery_fee=Decimal("5.00"), checkpoint_fee=Decimal("15.00"), total=Decimal("120.00"),
            merchant_arrived_at=timezone.now(),
        )
        captain_client = APIClient(); captain_client.force_authenticate(captain_user)
        response = captain_client.post(f"/api/orders/{order.id}/status/", {"status": "picked_up"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        settlement = CashSettlement.objects.get(order=order)
        self.assertEqual(settlement.amount, Decimal("120.00"))
        self.assertEqual(settlement.goods_amount, Decimal("100.00"))
        self.assertEqual(settlement.platform_commission, Decimal("10.00"))
        self.assertEqual(settlement.merchant_net, Decimal("90.00"))
        self.assertEqual(settlement.captain_earnings, Decimal("20.00"))
        # The captain can begin delivery without a premature merchant cash confirmation.
        response = captain_client.post(f"/api/orders/{order.id}/status/", {"status": "delivering"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = captain_client.post(f"/api/orders/{order.id}/status/", {"status": "completed"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = captain_client.post(f"/api/settlements/{settlement.id}/confirm/", {"collected_amount": "120.00"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["confirmed_by_captain"])
        merchant_client = APIClient(); merchant_client.force_authenticate(merchant_user)
        response = merchant_client.post(f"/api/settlements/{settlement.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["closed"])
        self.assertEqual(settlement.events.count(), 2)

    def test_under_collection_does_not_auto_close(self):
        from rest_framework.test import APIClient
        from .models import CaptainProfile, CashSettlement
        merchant_user = get_user_model().objects.create_user(username="short-shop", password="shop-password-123", role="merchant")
        captain_user = get_user_model().objects.create_user(username="short-captain", password="captain-password-123", role="captain")
        customer = get_user_model().objects.create_user(username="short-customer", password="customer-password-123", role="customer")
        merchant = MerchantProfile.objects.create(user=merchant_user, shop_name="Short Shop")
        captain = CaptainProfile.objects.create(user=captain_user)
        order = Order.objects.create(customer=customer, merchant=merchant, captain=captain, status="completed", total=Decimal("50.00"))
        settlement = CashSettlement.objects.create(order=order, merchant=merchant, captain=captain, amount=Decimal("50.00"), reference="SHORT-CASH-001")
        c = APIClient(); c.force_authenticate(captain_user)
        r = c.post(f"/api/settlements/{settlement.id}/confirm/", {"collected_amount": "45.00"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        m = APIClient(); m.force_authenticate(merchant_user)
        r = m.post(f"/api/settlements/{settlement.id}/confirm/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(r.data["closed"])

class RoadRoutingEndpointTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.customer = get_user_model().objects.create_user(
            username="route-customer", password="customer-password-123", role="customer"
        )
        self.other = get_user_model().objects.create_user(
            username="route-other", password="customer-password-123", role="customer"
        )
        self.order = Order.objects.create(
            customer=self.customer, order_type="ride", status="assigned",
            pickup_latitude=Decimal("31.768300"), pickup_longitude=Decimal("35.213700"),
            dropoff_latitude=Decimal("31.780000"), dropoff_longitude=Decimal("35.220000"),
        )
        self.client = APIClient()

    def test_order_owner_can_request_road_route(self):
        from unittest.mock import patch
        self.client.force_authenticate(self.customer)
        route = {"available": True, "distance_meters": 2300, "duration_seconds": 420,
                 "geometry": [[35.2137, 31.7683], [35.22, 31.78]], "source": "road_network"}
        with patch("core.views.road_route", return_value=route):
            response = self.client.get(
                f"/api/routing/route/?order={self.order.id}&start_lat=31.7683&start_lon=35.2137&end_lat=31.78&end_lon=35.22"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["distance_meters"], 2300)
        self.assertEqual(response.data["duration_seconds"], 420)

    def test_other_customer_cannot_request_route_for_order(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(
            f"/api/routing/route/?order={self.order.id}&start_lat=31.7683&start_lon=35.2137&end_lat=31.78&end_lon=35.22"
        )
        self.assertEqual(response.status_code, 403)

class CaptainLocationFreshnessTests(TestCase):
    def test_order_api_marks_old_captain_location_as_stale(self):
        from .models import CaptainProfile
        from .serializers import OrderSerializer
        from django.utils import timezone
        captain_user = get_user_model().objects.create_user(
            username="freshness-captain", password="captain-password-123", role="captain"
        )
        captain = CaptainProfile.objects.create(
            user=captain_user, current_latitude=Decimal("31.768300"),
            current_longitude=Decimal("35.213700"),
            current_location_updated_at=timezone.now() - timedelta(minutes=3),
        )
        customer = get_user_model().objects.create_user(
            username="freshness-customer", password="customer-password-123", role="customer"
        )
        order = Order.objects.create(customer=customer, captain=captain, order_type="ride", status="delivering")
        payload = OrderSerializer(order).data
        self.assertFalse(payload["captain_location_is_fresh"])
        self.assertGreaterEqual(payload["captain_location_age_seconds"], 180)
