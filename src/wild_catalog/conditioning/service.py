class LogitConditioner:
    def __init__(self, gamma: float, epsilon: float, top_k: int) -> None:
        self._gamma = gamma
        self._epsilon = epsilon
        self._top_k = top_k
