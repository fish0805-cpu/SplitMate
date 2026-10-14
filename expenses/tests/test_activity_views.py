from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import reverse

from expenses.models import Activity, Expense, Member


class ResponsiveAssetTests(SimpleTestCase):
    def test_mobile_hero_clips_rotated_decoration_without_page_overflow(self):
        stylesheet = (
            Path(settings.BASE_DIR)
            / "expenses"
            / "static"
            / "expenses"
            / "css"
            / "style.css"
        ).read_text(encoding="utf-8")

        self.assertIn(".hero-art { overflow: clip;", stylesheet)


class HomeViewTests(TestCase):
    def test_hero_lead_does_not_force_a_line_break(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertContains(
            response,
            '<p class="hero-lead">一起記錄支出，簡單完成分帳。</p>',
            html=True,
        )

    def test_hero_uses_most_recently_created_activity_and_its_totals(self):
        older = Activity.objects.create(name="舊活動")
        old_member = Member.objects.create(activity=older, name="Kai")
        Expense.objects.create(
            activity=older,
            title="舊支出",
            amount=Decimal("999.00"),
            paid_by=old_member,
        )
        newest = Activity.objects.create(name="週五晚餐")
        payer = Member.objects.create(activity=newest, name="Amy")
        Member.objects.create(activity=newest, name="Tom")
        for title, amount in [("飲料", "90.00"), ("晚餐", "210.00")]:
            Expense.objects.create(
                activity=newest,
                title=title,
                amount=Decimal(amount),
                paid_by=payer,
            )

        response = self.client.get(reverse("expenses:home"))
        hero = response.content.decode().split('<div class="hero-art"', 1)[1].split(
            "</section>", 1
        )[0]

        self.assertIn("週五晚餐", hero)
        self.assertIn("NT$ 300", hero)
        self.assertIn("2 位成員", hero)
        self.assertIn("2 筆共同支出", hero)
        self.assertNotIn("舊活動", hero)

    def test_hero_without_activities_shows_no_sample_numbers(self):
        response = self.client.get(reverse("expenses:home"))
        hero = response.content.decode().split('<div class="hero-art"', 1)[1].split(
            "</section>", 1
        )[0]

        self.assertIn("建立第一個活動", hero)
        self.assertNotIn("週五晚餐", hero)
        self.assertNotIn("NT$ 11,000", hero)

    def test_home_uses_activity_language_and_link(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertContains(response, "建立新活動")
        self.assertContains(response, "/activities/new/")
        self.assertContains(response, "目前的活動")

    def test_legacy_trip_urls_redirect_to_activity_urls(self):
        activity = Activity.objects.create(name="週五晚餐")

        for old_path, new_path in [
            ("/trips/new/", "/activities/new/"),
            (f"/trips/{activity.pk}/", f"/activities/{activity.pk}/"),
            (
                f"/trips/{activity.pk}/expenses/new/",
                f"/activities/{activity.pk}/expenses/new/",
            ),
            (
                f"/trips/{activity.pk}/settlement/",
                f"/activities/{activity.pk}/settlement/",
            ),
        ]:
            with self.subTest(old_path=old_path):
                response = self.client.get(old_path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], new_path)

    def test_home_renders_hero_and_empty_state(self):
        response = self.client.get(reverse("expenses:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Split expenses.")
        self.assertContains(response, "Not friendships.")
        self.assertContains(response, "建立新活動")
        self.assertContains(response, "還沒有活動")
        self.assertContains(response, "<main>", count=1)
        self.assertContains(response, "<h1>", count=1)
        self.assertContains(response, "/static/expenses/css/style.css")

    def test_home_lists_activity_member_count_and_total(self):
        activity = Activity.objects.create(name="Tokyo Trip")
        members = [
            Member.objects.create(activity=activity, name=name)
            for name in ["Kai", "Kevin", "Amy", "Tom"]
        ]
        for title, amount, payer in [
            ("晚餐", "2400.00", members[0]),
            ("飯店", "8000.00", members[2]),
            ("計程車", "600.00", members[1]),
        ]:
            Expense.objects.create(
                activity=activity,
                title=title,
                amount=Decimal(amount),
                paid_by=payer,
            )

        response = self.client.get(reverse("expenses:home"))

        self.assertContains(response, "Tokyo Trip")
        self.assertContains(response, "4 位成員")
        self.assertContains(
            response,
            '<p class="money">NT$ 11,000</p>',
            html=True,
        )
        self.assertContains(response, reverse("expenses:activity_detail", args=[activity.pk]))


class CreateActivityViewTests(TestCase):
    def _post_data(self, names, deleted_indexes=()):
        data = {
            "name": "Tokyo Trip",
            "members-TOTAL_FORMS": str(len(names)),
            "members-INITIAL_FORMS": "0",
            "members-MIN_NUM_FORMS": "2",
            "members-MAX_NUM_FORMS": "1000",
        }
        for index, name in enumerate(names):
            data[f"members-{index}-name"] = name
            if index in deleted_indexes:
                data[f"members-{index}-DELETE"] = "on"
        return data

    def test_get_create_activity_starts_with_two_member_rows(self):
        response = self.client.get(reverse("expenses:create_activity"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["member_formset"].total_form_count(), 2)
        self.assertContains(response, 'for="id_name"')
        self.assertContains(response, 'for="id_members-0-name"')
        self.assertContains(response, 'for="id_members-1-name"')
        self.assertContains(response, "<main>", count=1)
        self.assertContains(response, "<h1>", count=1)

    def test_valid_post_creates_activity_and_members_then_redirects(self):
        response = self.client.post(
            reverse("expenses:create_activity"),
            self._post_data(["Kai", "Kevin"]),
        )

        activity = Activity.objects.get(name="Tokyo Trip")
        self.assertRedirects(
            response,
            reverse("expenses:activity_detail", args=[activity.pk]),
        )
        self.assertQuerySetEqual(
            activity.members.order_by("pk").values_list("name", flat=True),
            ["Kai", "Kevin"],
        )

    def test_fewer_than_two_members_is_rejected(self):
        response = self.client.post(
            reverse("expenses:create_activity"),
            self._post_data(["Kai", ""]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "至少需要 2 位成員")
        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(Member.objects.count(), 0)

    def test_case_insensitive_duplicate_members_roll_back_entire_activity(self):
        response = self.client.post(
            reverse("expenses:create_activity"),
            self._post_data(["Kai", "kai"]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "成員名稱不可重複")
        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(Member.objects.count(), 0)

    def test_invalid_activity_announces_error_summary(self):
        data = self._post_data(["Kai", "Kevin"])
        data["name"] = ""

        response = self.client.post(reverse("expenses:create_activity"), data)

        self.assertContains(response, 'role="alert"')

    def test_deleted_or_blank_extra_rows_do_not_count_as_members(self):
        response = self.client.post(
            reverse("expenses:create_activity"),
            self._post_data(["Kai", "Kevin", "", "Amy"], deleted_indexes=(3,)),
        )

        activity = Activity.objects.get(name="Tokyo Trip")
        self.assertRedirects(
            response,
            reverse("expenses:activity_detail", args=[activity.pk]),
        )
        self.assertQuerySetEqual(
            activity.members.order_by("pk").values_list("name", flat=True),
            ["Kai", "Kevin"],
        )

