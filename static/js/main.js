
/* ========== blog.html ========== */

<script>
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
</script>