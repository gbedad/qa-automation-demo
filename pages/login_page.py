from pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/"

    @property
    def username(self):
        return self.by_test_id("username")

    @property
    def password(self):
        return self.by_test_id("password")

    @property
    def submit(self):
        return self.by_test_id("login-button")

    @property
    def error(self):
        return self.by_test_id("error")

    def login(self, user: str, password: str):
        self.username.fill(user)
        self.password.fill(password)
        self.submit.click()
