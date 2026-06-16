const chatContainer = document.getElementById('chat_container');
const userInput = document.getElementById('user_input');
const sendBtn = document.getElementById('send_btn');
const clearBtn = document.getElementById('clear_btn');
const topKInput = document.getElementById('top_k');

function addMessage(content, isUser) {
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'assistant'}`;
    div.textContent = content;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return div;
}

async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;
    
    userInput.value = '';
    addMessage(text, true);
    
    const responseDiv = document.createElement('div');
    responseDiv.className = 'message assistant';
    
    const statusDiv = document.createElement('div');
    statusDiv.className = 'system-status';
    statusDiv.textContent = '[SYS] Analyzing vectors...';
    responseDiv.appendChild(statusDiv);
    
    const contentDiv = document.createElement('div');
    responseDiv.appendChild(contentDiv);
    chatContainer.appendChild(responseDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const top_k = parseInt(topKInput.value);
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text, top_k})
        });
        
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        statusDiv.textContent = '[SYS] Streaming output...';
        
        let fullText = "";
        let metaParsed = false;
        
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            
            fullText += decoder.decode(value, {stream: true});
            
            if (!metaParsed && fullText.includes('__META_END__\n')) {
                const metaEndIdx = fullText.indexOf('__META_END__\n') + '__META_END__\n'.length;
                const metaBlock = fullText.substring(0, metaEndIdx);
                fullText = fullText.substring(metaEndIdx);
                metaParsed = true;
                
                try {
                    const jsonStr = metaBlock.replace('__META__:', '').replace('__META_END__\n', '');
                    const metaObj = JSON.parse(jsonStr);
                    statusDiv.innerHTML = `[SYS] Stream Complete. <br><span style="color:#d4af2a;">MODE:</span> ${metaObj.mode} | <span style="color:#d4af2a;">URGENCY:</span> ${metaObj.urgency} <br><span style="color:#d4af2a;">PERSONA:</span> ${metaObj.persona}`;
                } catch(e) {
                    console.error("Meta parse error", e);
                }
            }
            
            if (metaParsed) {
                contentDiv.innerHTML = marked.parse(fullText);
            }
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    } catch (err) {
        statusDiv.textContent = '[ERR] Critical Failure';
        contentDiv.textContent = err.message;
    }
}

sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

clearBtn.addEventListener('click', async () => {
    await fetch('/api/clear_memory', {method: 'POST'});
    addMessage('[SYS] Memory cleared.', false);
});
