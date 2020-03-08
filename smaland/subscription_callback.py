

class SubscriptionCallback:

    def __init__(self):
        self._context = {}

    def _callback(self, message):
        """This function will be called on new message"""
        print(message)