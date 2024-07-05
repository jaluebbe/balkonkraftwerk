import logging
import arrow
import tibber


class tibber_price:
    def __init__(self, tibber_api_key: str) -> None:
        self.tibber_api_key = tibber_api_key
        self.setup()

    def setup(self) -> None:
        try:
            self.account = tibber.Account(self.tibber_api_key)
        except:
            logging.exception("failed to connect to Tibber API.")
            self.account = None

    def get_price(self) -> dict:
        price_info = self.account.homes[0].current_subscription.price_info
        if price_info.current.starts_at is None:
            self.account.update()
        elif (
            arrow.now() - arrow.get(price_info.current.starts_at)
        ).seconds >= 3600:
            self.account.update()
        else:
            return price_info.current.cache
        price_info = self.account.homes[0].current_subscription.price_info
        return price_info.current.cache

    def process_report(self, report: dict) -> None:
        if self.account is not None:
            _price = self.get_price()
            if len(_price) > 0:
                report["tibber_price"] = _price
