class ConversationMemory:
    def __init__(self, max_turns=3):
        self.max_turns = max_turns
        self.history = []

    def add_interaction(self, user_query, assistant_response):
        self.history.append({"user": user_query, "assistant": assistant_response})
        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def get_context_string(self):
        if not self.history:
            return ""
        
        ctx = "PREVIOUS CONTEXT (SUMMARY):\n"
        for turn in self.history:
            ctx += f"User: {turn['user']}\n"
            clean_ast = turn['assistant'].replace('\n', ' ')
            snippet = clean_ast[:200] + "..." if len(clean_ast) > 200 else clean_ast
            ctx += f"Assistant previously advised: {snippet}\n"
        ctx += "\n"
        return ctx
        
    def clear(self):
        self.history = []
