class AlertSystem:
    def __init__(self):
        pass

    def send_alert(self, message, priority='MEDIUM'):
        print(f"[{priority}] ALERT: {message}")
        # Add integration with Email/SMS/Slack here
