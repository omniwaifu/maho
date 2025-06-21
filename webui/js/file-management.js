// File Management Module
// Handles file uploads, attachments, and file operations

import { sendJsonData } from './core-utils.js';
import { toast, toastFetchError } from './toast-system.js';
import { getContext } from './chat-core.js';

export function handleFiles(files, inputAD) {
    if (!inputAD) {
        console.error('inputAD is required for handleFiles');
        return;
    }

    if (!inputAD.attachments) {
        inputAD.attachments = [];
    }

    for (const file of files) {
        const attachment = {
            file: file,
            name: file.name,
            size: file.size,
            type: getFileType(file)
        };

        // Add preview for images
        if (attachment.type === 'image') {
            const reader = new FileReader();
            reader.onload = (e) => {
                attachment.preview = e.target.result;
            };
            reader.readAsDataURL(file);
        }

        inputAD.attachments.push(attachment);
    }

    inputAD.hasAttachments = inputAD.attachments.length > 0;
    console.log('Files handled:', inputAD.attachments);
}

function getFileType(file) {
    if (file.type.startsWith('image/')) {
        return 'image';
    } else if (file.type.startsWith('text/') || file.name.endsWith('.txt') || file.name.endsWith('.md')) {
        return 'text';
    } else if (file.type === 'application/pdf') {
        return 'pdf';
    } else if (file.type.startsWith('audio/')) {
        return 'audio';
    } else if (file.type.startsWith('video/')) {
        return 'video';
    } else {
        return 'file';
    }
}

export function removeAttachment(index, inputAD) {
    if (inputAD && inputAD.attachments) {
        inputAD.attachments.splice(index, 1);
        inputAD.hasAttachments = inputAD.attachments.length > 0;
    }
}

// Knowledge import functionality
export async function loadKnowledge() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.txt,.pdf,.csv,.html,.json,.md';
    input.multiple = true;

    return new Promise((resolve, reject) => {
        input.onchange = async () => {
            try {
                const formData = new FormData();
                for (let file of input.files) {
                    formData.append('files[]', file);
                }

                formData.append('ctxid', getContext());

                const response = await fetch('/api/v1/import_knowledge', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    toast(errorText, "error");
                    reject(new Error(errorText));
                } else {
                    const data = await response.json();
                    toast("Knowledge files imported: " + data.filenames.join(", "), "success");
                    resolve(data);
                }
            } catch (error) {
                toastFetchError("Error importing knowledge files", error);
                reject(error);
            }
        };

        input.click();
    });
}

// Work directory file operations
export async function uploadWorkDirFiles() {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;

    return new Promise((resolve, reject) => {
        input.onchange = async () => {
            try {
                const formData = new FormData();
                for (let file of input.files) {
                    formData.append('files[]', file);
                }

                formData.append('context', getContext());

                const response = await fetch('/api/v1/upload_work_dir_files', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    toast(errorText, "error");
                    reject(new Error(errorText));
                } else {
                    const data = await response.json();
                    toast("Files uploaded successfully", "success");
                    resolve(data);
                }
            } catch (error) {
                toastFetchError("Error uploading files", error);
                reject(error);
            }
        };

        input.click();
    });
}

export async function downloadWorkDirFile(filename) {
    try {
        const response = await fetch(`/api/v1/download_work_dir_file?context=${getContext()}&filename=${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        toast(`Downloaded ${filename}`, "success");
    } catch (error) {
        toastFetchError("Error downloading file", error);
    }
}

export async function deleteWorkDirFile(filename) {
    try {
        const response = await sendJsonData('/api/v1/delete_work_dir_file', {
            context: getContext(),
            filename: filename
        });

        if (response.success) {
            toast(`Deleted ${filename}`, "success");
            return true;
        } else {
            toast(`Failed to delete ${filename}`, "error");
            return false;
        }
    } catch (error) {
        toastFetchError("Error deleting file", error);
        return false;
    }
}

export async function getWorkDirFiles() {
    try {
        const response = await sendJsonData('/api/v1/get_work_dir_files', {
            context: getContext()
        });

        return response.files || [];
    } catch (error) {
        toastFetchError("Error getting work directory files", error);
        return [];
    }
}

// File size formatting utility
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Global exports for backward compatibility
window.loadKnowledge = loadKnowledge;
window.handleFiles = handleFiles;
window.uploadWorkDirFiles = uploadWorkDirFiles;
window.downloadWorkDirFile = downloadWorkDirFile;
window.deleteWorkDirFile = deleteWorkDirFile; 