"""Selected adapter boundary; SEC bounded filing integration is unverified."""
class IntegrationUnavailable(RuntimeError):
    pass


class SECProvider:
    def fetch(self, domain, start, end):
        raise IntegrationUnavailable('SEC bounded filing discovery, retrieval and parser integration are not implemented or validated')

    def normalize(self, domain, rows):
        raise IntegrationUnavailable('SEC filing parser integration is not implemented or validated')
