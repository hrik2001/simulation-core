class HistoricalSpotPriceNotFoundError(Exception):
    """
    Exception raised when historical price cannot be fetched due to logical limitation
    """

    def __init__(self, message="Historical Spot Price Not Found"):
        self.message = message
        super().__init__(self.message)


class AuctionDoesNotExist(Exception):
    """
    Exception raised when auction doesn't exist
    """

    def __init__(self, message="Auction doesn't exist"):
        self.message = message
        super().__init__(self.message)


class AuctionDoesExist(Exception):
    """
    Exception raised when auction already exist
    """

    def __init__(self, message="Auction exist"):
        self.message = message
        super().__init__(self.message)


class AccountNotLiquidatable(Exception):
    """
    Exception raised when account is not liquidatable
    """

    def __init__(self, message="Account is not liquidatable"):
        self.message = message
        super().__init__(self.message)


class NotEnoughLiquidity(Exception):
    """
    Exception raised when liquidity isn't enough
    """

    def __init__(self, message="Not enough liquidity"):
        self.message = message
        super().__init__(self.message)


class PriceNotPopulated(Exception):
    """
    Exception raised when cached pricing data isn't available for a simulation
    """

    def __init__(self, message="Not enough liquidity"):
        self.message = message
        super().__init__(self.message)
