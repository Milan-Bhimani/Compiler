document.getElementById('save').addEventListener('click', function() {
    const content = document.getElementById('editor').innerText;
    const title = prompt('Enter file name:');
    fetch('/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `content=${encodeURIComponent(content)}&title=${encodeURIComponent(title)}`,
    }).then(response => response.text()).then(data => {
        alert(data);
    });
});

document.getElementById('download').addEventListener('click', function() {
    const content = document.getElementById('editor').innerText;
    const title = prompt('Enter file name:');
    fetch('/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `content=${encodeURIComponent(content)}&title=${encodeURIComponent(title)}`,
    }).then(response => response.blob()).then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `${title}.txt`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.getElementById('editor').innerText = '';
    });
});

document.getElementById('new').addEventListener('click', function() {
    document.getElementById('editor').innerText = '';
});

document.getElementById('open-btn').addEventListener('click', function() {
    document.getElementById('open').click();
});

document.getElementById('open').addEventListener('change', function(event) {
    const file = event.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    fetch('/open', {
        method: 'POST',
        body: formData,
    }).then(response => response.text()).then(data => {
        document.getElementById('editor').innerText = data;
    });
});

editor.setTheme("ace/theme/dracula");