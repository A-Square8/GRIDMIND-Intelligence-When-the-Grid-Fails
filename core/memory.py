class ConversationMemory:
    def __init__(self, max_turns=3, db=None, conversation_id=None):
        self.max_turns = max_turns
        self.history = []
        self.db = db
        self.conversation_id = conversation_id

    def add_interaction(self, user_query, assistant_response, metadata=None):
        self.history.append({"user": user_query, "assistant": assistant_response})
        if len(self.history) > self.max_turns:
            self.history.pop(0)

        if self.db and self.conversation_id:
            self.db.save_message(self.conversation_id, "user", user_query, metadata)
            self.db.save_message(self.conversation_id, "assistant", assistant_response, metadata)

    def get_context_string(self):
        if not self.history:
            return ""

        ctx = "PREVIOUS CONTEXT (SUMMARY):\n"
        for turn in self.history:
            ctx += f"User: {turn['user']}\n"
            clean_ast = turn["assistant"].replace("\n", " ")
            snippet = clean_ast[:200] + "..." if len(clean_ast) > 200 else clean_ast
            ctx += f"Assistant previously advised: {snippet}\n"
        ctx += "\n"
        return ctx

    def set_conversation(self, conversation_id):
        self.conversation_id = conversation_id
        self.history = []

        if self.db and conversation_id:
            history = self.db.get_conversation_history(conversation_id, limit=self.max_turns * 2)
            pairs = []
            current_user = None
            for msg in history:
                if msg["role"] == "user":
                    current_user = msg["content"]
                elif msg["role"] == "assistant" and current_user:
                    pairs.append({"user": current_user, "assistant": msg["content"]})
                    current_user = None
            self.history = pairs[-self.max_turns:]

    def clear(self):
        self.history = []
        if self.db and self.conversation_id:
            pass
