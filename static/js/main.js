/* ========== blog.html ========== */


document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-share-url]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const url = this.dataset.shareUrl;
            const title = this.dataset.shareTitle || document.title;

            if (navigator.share) {
                navigator.share({ title: title, url: url }).catch(function () {});
            } else {
                window.prompt("Kopieer deze link om te delen:", url);
            }
        });
    });
});



/* ========== dialoog_thread.html ========== */


document.addEventListener("DOMContentLoaded", function () {
    const uploadUrl = document.body.dataset.uploadImageUrl || "";

    if (window.tinymce && document.querySelector("textarea.comment-editor, textarea.thread-editor")) {
        tinymce.init({
            selector: 'textarea.comment-editor, textarea.thread-editor',
            plugins: 'link lists image media code emoticons',
            menubar: false,
            toolbar: 'undo redo | bold italic | bullist numlist | link image media emoticons | code',
            automatic_uploads: true,
            images_upload_url: uploadUrl,
            images_upload_credentials: true,
            media_live_embeds: true,
            extended_valid_elements: 'iframe[src|frameborder|style|scrolling|class|width|height|name|align|allowfullscreen]'
        });
    }

    document.querySelectorAll("[data-reply-toggle]").forEach(function (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const commentId = this.getAttribute("data-reply-toggle");
            const form = document.getElementById("reply-form-" + commentId);
            if (form) {
                form.style.display = form.style.display === "none" ? "block" : "none";
            }
        });
    });

    document.querySelectorAll("[data-edit-toggle]").forEach(function (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const commentId = this.getAttribute("data-edit-toggle");
            const form = document.getElementById("edit-form-" + commentId);
            if (form) {
                form.style.display = form.style.display === "none" ? "block" : "none";
            }
        });
    });

    const threadEditForm   = document.getElementById("thread-edit-form");
    const threadEditBtns   = document.querySelectorAll("[data-thread-edit-toggle]");
    if (threadEditForm && threadEditBtns.length) {
        threadEditBtns.forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                const isHidden =
                    threadEditForm.style.display === "none" ||
                    threadEditForm.style.display === "";
                threadEditForm.style.display = isHidden ? "block" : "none";
                if (isHidden) {
                    threadEditForm.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
    }

    const newToggle = document.getElementById("toggle-new-comment");
    const newForm   = document.getElementById("new-comment-form");
    if (newToggle && newForm) {
        newToggle.addEventListener("click", function (e) {
            e.preventDefault();
            newForm.style.display =
                newForm.style.display === "none" || newForm.style.display === ""
                ? "block"
                : "none";
        });
    }

    if (!("speechSynthesis" in window)) {
        const info = document.getElementById("tts-support-info");
        if (info) {
            info.textContent = "Voorleesfunctie wordt niet ondersteund door deze browser.";
        }
    } else {
        const synth = window.speechSynthesis;
        let utterance = null;

        const playBtn   = document.getElementById("tts-play");
        const pauseBtn  = document.getElementById("tts-pause");
        const stopBtn   = document.getElementById("tts-stop");
        const rateInput = document.getElementById("tts-rate");
        const rateValue = document.getElementById("tts-rate-value");
        const contentEl = document.getElementById("thread-content");

        function getText() {
            if (!contentEl) return "";
            return contentEl.innerText || contentEl.textContent || "";
        }

        function startReading() {
            const text = getText().trim();
            if (!text) return;

            if (synth.speaking || synth.paused) {
                synth.cancel();
            }

            utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "nl-NL";
            utterance.rate = parseFloat(rateInput.value) || 1.0;

            synth.speak(utterance);
        }

        function togglePause() {
            if (synth.speaking && !synth.paused) {
                synth.pause();
            } else if (synth.paused) {
                synth.resume();
            }
        }

        function stopReading() {
            if (synth.speaking || synth.paused) {
                synth.cancel();
            }
        }

        if (playBtn) {
            playBtn.addEventListener("click", function (e) {
                e.preventDefault();
                startReading();
            });
        }
        if (pauseBtn) {
            pauseBtn.addEventListener("click", function (e) {
                e.preventDefault();
                togglePause();
            });
        }
        if (stopBtn) {
            stopBtn.addEventListener("click", function (e) {
                e.preventDefault();
                stopReading();
            });
        }

        if (rateInput && rateValue) {
            rateInput.addEventListener("input", function () {
                rateValue.textContent = rateInput.value;
            });
        }

        window.addEventListener("beforeunload", function () {
            if (synth.speaking || synth.paused) {
                synth.cancel();
            }
        });
    }

    document.querySelectorAll("[data-share-url]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const url = this.dataset.shareUrl;
            const title = this.dataset.shareTitle || document.title;

            if (navigator.share) {
                navigator.share({ title: title, url: url }).catch(function () {});
            } else {
                window.prompt("Kopieer deze link om te delen:", url);
            }
        });
    });
});


/* ========== dialoog.html ========== */


document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-share-url]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const url = this.dataset.shareUrl;
            const title = this.dataset.shareTitle || document.title;

            if (navigator.share) {
                navigator.share({ title: title, url: url }).catch(function () {});
            } else {
                window.prompt("Kopieer deze link om te delen:", url);
            }
        });
    });
});


/* ========== edit_blog.html ========== */


document.addEventListener("DOMContentLoaded", function () {
    const uploadUrl = document.body.dataset.uploadImageUrl || "";

    if (window.tinymce && document.querySelector("#content")) {
        if (tinymce.get("content")) {
            tinymce.get("content").remove();
        }

        tinymce.init({
            selector: '#content',
            plugins: 'link lists image media code',
            toolbar: 'undo redo | blocks | bold italic | ' +
                     'alignleft aligncenter alignright | bullist numlist | ' +
                     'link image media | code',
            automatic_uploads: true,
            images_upload_url: uploadUrl,
            images_upload_credentials: true,
            media_live_embeds: true,
            extended_valid_elements: 'iframe[src|frameborder|style|scrolling|class|width|height|name|align|allowfullscreen]'
        });
    }
});


/* ========== new_blog.html ========== */


document.addEventListener("DOMContentLoaded", function () {
    const uploadUrl = document.body.dataset.uploadImageUrl || "";

    if (window.tinymce && document.querySelector("#content")) {
        if (tinymce.get("content")) {
            tinymce.get("content").remove();
        }

        tinymce.init({
            selector: '#content',
            plugins: 'link lists image media code',
            toolbar: 'undo redo | blocks | bold italic | ' +
                     'alignleft aligncenter alignright | bullist numlist | ' +
                     'link image media | code',
            automatic_uploads: true,
            images_upload_url: uploadUrl,
            images_upload_credentials: true,
            media_live_embeds: true,
            extended_valid_elements: 'iframe[src|frameborder|style|scrolling|class|width|height|name|align|allowfullscreen]'
        });
    }
});


/* ========== new_dialoog.html ========== */


tinymce.init({
    selector: '#body',
    plugins: 'link lists image media code emoticons',
    menubar: false,
    toolbar: 'undo redo | blocks | bold italic | ' +
             'alignleft aligncenter alignright | bullist numlist | ' +
             'link image media emoticons | code',
    automatic_uploads: true,
    images_upload_url: "{{ url_for('upload_image') }}",
    images_upload_credentials: true,
    media_live_embeds: true,
    extended_valid_elements: 'iframe[src|frameborder|style|scrolling|class|width|height|name|align|allowfullscreen]'
});


/* ========== view_blog.html ========== */


document.addEventListener("DOMContentLoaded", function () {
    const uploadUrl = document.body.dataset.uploadImageUrl || "";

    if (window.tinymce && document.querySelector("#content")) {
        if (tinymce.get("content")) {
            tinymce.get("content").remove();
        }

        tinymce.init({
            selector: '#content',
            plugins: 'link lists image media code',
            toolbar: 'undo redo | blocks | bold italic | ' +
                     'alignleft aligncenter alignright | bullist numlist | ' +
                     'link image media | code',
            automatic_uploads: true,
            images_upload_url: uploadUrl,
            images_upload_credentials: true,
            media_live_embeds: true,
            extended_valid_elements: 'iframe[src|frameborder|style|scrolling|class|width|height|name|align|allowfullscreen]'
        });
    }

    if (!("speechSynthesis" in window)) {
        const info = document.getElementById("tts-support-info");
        if (info) {
            info.textContent = "Voorleesfunctie wordt niet ondersteund door deze browser.";
        }
    } else {
        const synth = window.speechSynthesis;
        let utterance = null;

        const playBtn  = document.getElementById("tts-play");
        const pauseBtn = document.getElementById("tts-pause");
        const stopBtn  = document.getElementById("tts-stop");
        const rateInput = document.getElementById("tts-rate");
        const rateValue = document.getElementById("tts-rate-value");
        const contentEl = document.getElementById("blog-content");

        function getText() {
            if (!contentEl) return "";
            return contentEl.innerText || contentEl.textContent || "";
        }

        function startReading() {
            const text = getText().trim();
            if (!text) return;

            if (synth.speaking || synth.paused) {
                synth.cancel();
            }

            utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "nl-NL";
            utterance.rate = parseFloat(rateInput.value) || 1.0;

            synth.speak(utterance);
        }

        function togglePause() {
            if (synth.speaking && !synth.paused) {
                synth.pause();
            } else if (synth.paused) {
                synth.resume();
            }
        }

        function stopReading() {
            if (synth.speaking || synth.paused) {
                synth.cancel();
            }
        }

        if (playBtn) {
            playBtn.addEventListener("click", function (e) {
                e.preventDefault();
                startReading();
            });
        }
        if (pauseBtn) {
            pauseBtn.addEventListener("click", function (e) {
                e.preventDefault();
                togglePause();
            });
        }
        if (stopBtn) {
            stopBtn.addEventListener("click", function (e) {
                e.preventDefault();
                stopReading();
            });
        }

        if (rateInput && rateValue) {
            rateInput.addEventListener("input", function () {
                rateValue.textContent = rateInput.value;
            });
        }

        window.addEventListener("beforeunload", function () {
            if (synth.speaking || synth.paused) {
                synth.cancel();
            }
        });
    }

    document.querySelectorAll("[data-share-url]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const url = this.dataset.shareUrl;
            const title = this.dataset.shareTitle || document.title;

            if (navigator.share) {
                navigator.share({ title: title, url: url }).catch(function () {});
            } else {
                window.prompt("Kopieer deze link om te delen:", url);
            }
        });
    });

    const blogEditForm = document.getElementById("blog-edit-form");
    const blogEditBtns = document.querySelectorAll("[data-blog-edit-toggle]");
    if (blogEditForm && blogEditBtns.length) {
        blogEditBtns.forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                const isHidden =
                    blogEditForm.style.display === "none" ||
                    blogEditForm.style.display === "";
                blogEditForm.style.display = isHidden ? "block" : "none";
                if (isHidden) {
                    blogEditForm.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
    }
});
