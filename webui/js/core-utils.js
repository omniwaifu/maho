// Core Utilities Module
// Pure functions with no side effects or external dependencies

export function generateGUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

export const sendJsonData = async function (url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    return await response.json();
}

export function downloadFile(filename, content) {
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

export function isMobile() {
    return window.innerWidth <= 768;
}

export function safeAlpineData(element) {
    return window.Alpine ? Alpine.$data(element) : null;
}

export function addClassToElement(element, className) {
    if (element && !element.classList.contains(className)) {
        element.classList.add(className);
    }
}

export function removeClassFromElement(element, className) {
    if (element && element.classList.contains(className)) {
        element.classList.remove(className);
    }
}

export function adjustTextareaHeight() {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
    }
}

export function toggleCssProperty(selector, property, value) {
    const styleSheets = document.styleSheets;
    for (let i = 0; i < styleSheets.length; i++) {
        const styleSheet = styleSheets[i];
        const rules = styleSheet.cssRules || styleSheet.rules;
        for (let j = 0; j < rules.length; j++) {
            const rule = rules[j];
            if (rule.selectorText == selector) {
                if (value === undefined) {
                    rule.style.removeProperty(property);
                } else {
                    rule.style.setProperty(property, value);
                }
                return;
            }
        }
    }
}

// File reading utility
export async function readJsonFiles() {
    return new Promise((resolve, reject) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.multiple = true;

        input.onchange = async () => {
            const files = Array.from(input.files);
            const fileContents = {};

            for (const file of files) {
                try {
                    const content = await file.text();
                    fileContents[file.name] = JSON.parse(content);
                } catch (error) {
                    console.error(`Error reading file ${file.name}:`, error);
                    reject(error);
                    return;
                }
            }
            resolve(fileContents);
        };

        input.click();
    });
}

// Global exports for backward compatibility
window.generateGUID = generateGUID;
window.sendJsonData = sendJsonData;
window.safeAlpineData = safeAlpineData; 