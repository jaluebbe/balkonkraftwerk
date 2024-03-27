import arrow
import tibber


class tibber_price:
    def __init__(self, tibber_api_key):
        self.account = tibber.Account(tibber_api_key)

    def get_price(self):
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
