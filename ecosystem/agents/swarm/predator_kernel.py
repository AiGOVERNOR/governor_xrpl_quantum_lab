class PredatorKernel:
    """
    AETHERBORN SWARM - Arbitrage Predator Kernel
    Chooses attack (trade size) based on bankroll.
    """

    def choose_trade_amount(self, bal):
        return max(10, int(bal * 0.00035))
