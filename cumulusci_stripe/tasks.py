import stripe
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg, process_list_arg



class BaseStripeTask(BaseTask):
    task_options = {
        "service_alias": {
            "description": "Use a non-default stripe service by specifying its alias",
        },
    }

    def _init_stripe(self):
        stripe.api_key = self.project_config.keychain.get_service(
            "stripe", self.options.get("service_alias")
        ).api_key

    def _init_task(self):
        self._init_stripe()


class CreateWebhook(BaseStripeTask):
    task_options = {
        "events": {
            "description": "A list of Stripe events to send to the webhook endpoint.  More info at https://stripe.com/docs/api/webhook_endpoints/create",
            "required": True,
        },
        "url": {
            "description": "The webhook endpoint url.  More info at https://stripe.com/docs/api/webhook_endpoints/create",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["events"] = process_list_arg(self.options.get("events"))

    def _check_existing(self):
        response = stripe.WebhookEndpoint.list(limit=100)
        for webhook in response.data:
            if webhook.url == self.options["url"]:
                raise TaskOptionsError(
                    f"Stripe webhook already exists for url {self.options['url']}"
                )

    def _run_task(self):
        self._check_existing()
        response = stripe.WebhookEndpoint.create(
            url=self.options["url"],
            enabled_events=self.options["events"],
        )
        self.logger.info(
            f"Created Stripe webhook endpoint for url {self.options['url']}"
        )
        self.return_values["secret"] = response.secret


class DeleteWebhook(BaseStripeTask):
    task_options = {
        "url": {
            "description": "The Stripe webhook endpoint target url to delete from Stripe",
            "required": True,
        },
        "ignore_missing": {
            "description": "If True, don't fail if the webhook endpoint doesn't exist.  Defaults to False",
        },
    }
    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["ignore_missing"] = process_bool_arg(self.options.get("ignore_missing", False))

    def _run_task(self):
        response = stripe.WebhookEndpoint.list(limit=100)
        for webhook in response.data:
            if webhook.url == self.options["url"]:
                stripe.WebhookEndpoint.delete(webhook.id)
                self.logger.info(
                    f"Deleted Stripe webhook endpoint with id {webhook.id}"
                )
                return
        if self.options["ignore_missing"] is False:
            raise TaskOptionsError(
                f"No Stripe webhook endpoint with target url={self.options['url']} found"
            )
        else:
            self.logger.info("Webhook endpoint not found, ignoring because ignore_missing is True")
