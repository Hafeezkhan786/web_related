/** @odoo-module **/

document.addEventListener('change', function (ev) {
    if (ev.target && ev.target.name === 'guest_star_rating') {
        var val = ev.target.value;
        var textElem = document.getElementById('guest_star_text');
        if (textElem) {
            var labels = {
                '5': '5 Stars - Excellent',
                '4': '4 Stars - Very Good',
                '3': '3 Stars - Good',
                '2': '2 Stars - Fair',
                '1': '1 Star - Poor'
            };
            textElem.textContent = labels[val] || (val + ' Stars');
        }
    }
});

document.addEventListener('click', async function (ev) {
    var btn = ev.target.closest('#submit_guest_rating_btn');
    if (!btn) return;
    ev.preventDefault();
    ev.stopPropagation();

    var modal = document.getElementById('psaeGuestRatingModal');
    if (!modal) return;

    var productId = btn.getAttribute('data-product-id') || modal.getAttribute('data-product-id');
    var selectedStar = modal.querySelector('input[name="guest_star_rating"]:checked');
    var ratingVal = selectedStar ? selectedStar.value : 0;
    var commentVal = (modal.querySelector('#guest_reviewer_comment') || {}).value || '';
    var nameVal = (modal.querySelector('#guest_reviewer_name') || {}).value || '';
    var emailVal = (modal.querySelector('#guest_reviewer_email') || {}).value || '';
    var errorDiv = modal.querySelector('#guest_rating_error');
    var successDiv = modal.querySelector('#guest_rating_success');

    function showError(msg) {
        if (errorDiv) {
            errorDiv.textContent = msg;
            errorDiv.classList.remove('d-none');
            errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    if (errorDiv) errorDiv.classList.add('d-none');
    if (successDiv) successDiv.classList.add('d-none');

    if (!ratingVal || parseInt(ratingVal) < 1) {
        showError('Please select a star rating (1 to 5 stars).');
        return;
    }

    if (!commentVal || !commentVal.trim()) {
        showError('Please write your review comment.');
        return;
    }

    if (!nameVal || !nameVal.trim()) {
        showError('Please enter your name.');
        return;
    }

    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailVal || !emailRegex.test(emailVal.trim())) {
        showError('Please enter a valid email address.');
        return;
    }

    btn.disabled = true;
    var originalBtnHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Submitting...';

    try {
        var response = await fetch('/website/guest_rating/post', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    product_id: parseInt(productId),
                    rating: parseInt(ratingVal),
                    name: nameVal.trim(),
                    email: emailVal.trim(),
                    feedback: commentVal.trim()
                }
            })
        });

        var data = await response.json();
        var result = (data && data.result) || {};

        if (result.error) {
            showError(result.error);
        } else if (result.success) {
            if (successDiv) {
                successDiv.textContent = result.message || 'Thank you! Your review has been submitted for admin approval.';
                successDiv.classList.remove('d-none');
                successDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            var form = modal.querySelector('#psae_guest_rating_form');
            if (form) form.reset();
            var starText = modal.querySelector('#guest_star_text');
            if (starText) starText.textContent = 'Select 1-5 Stars';

            setTimeout(function () {
                var closeBtn = modal.querySelector('[data-bs-dismiss="modal"]');
                if (closeBtn) closeBtn.click();
            }, 2500);
        } else {
            showError('An unexpected error occurred. Please try again.');
        }
    } catch (err) {
        console.error('Error submitting guest rating:', err);
        showError('Network error while submitting review. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalBtnHtml;
    }
});

// Dynamic Review Filtering & Numbered Pagination Controller (Image 2)
var currentReviewFilter = 'all';
var currentReviewPage = 1;
var reviewsPerPage = 3;

function updateReviewsPagination() {
    var container = document.querySelector('.psae-reviews-container');
    var pagWrap = document.getElementById('psae_reviews_pagination_wrap');
    if (!container) return;

    var allItems = Array.from(container.querySelectorAll('.psae-review-item'));
    if (!allItems.length) {
        if (pagWrap) pagWrap.innerHTML = '';
        return;
    }

    // Determine filtered items subset
    var filteredItems = [];

    if (currentReviewFilter === 'highest') {
        var ratings = allItems.map(function(el) { return parseFloat(el.getAttribute('data-rating') || 0); });
        var maxRating = Math.max.apply(null, ratings);
        filteredItems = allItems.filter(function(el) {
            return parseFloat(el.getAttribute('data-rating') || 0) === maxRating;
        });
    } else if (currentReviewFilter === 'lowest') {
        var ratings = allItems.map(function(el) { return parseFloat(el.getAttribute('data-rating') || 0); });
        var minRating = Math.min.apply(null, ratings);
        filteredItems = allItems.filter(function(el) {
            return parseFloat(el.getAttribute('data-rating') || 0) === minRating;
        });
    } else if (currentReviewFilter === 'recent') {
        var dates = allItems.map(function(el) {
            var raw = el.getAttribute('data-date') || '';
            return raw.split(' ')[0];
        }).filter(Boolean);
        dates.sort(function(a, b) { return new Date(b).getTime() - new Date(a).getTime(); });
        var latestDate = dates[0] || '';
        filteredItems = allItems.filter(function(el) {
            var raw = el.getAttribute('data-date') || '';
            return raw.split(' ')[0] === latestDate;
        });
    } else {
        // 'all' -> All items sorted by date descending
        allItems.sort(function (a, b) {
            var dA = new Date(a.getAttribute('data-date') || 0).getTime();
            var dB = new Date(b.getAttribute('data-date') || 0).getTime();
            return dB - dA;
        });
        allItems.forEach(function (el) { container.appendChild(el); });
        filteredItems = allItems;
    }

    // Hide all items not in filtered list
    allItems.forEach(function(el) {
        if (filteredItems.indexOf(el) === -1) {
            el.classList.add('d-none');
        }
    });

    var totalItems = filteredItems.length;
    var totalPages = Math.ceil(totalItems / reviewsPerPage);

    if (totalPages <= 1) {
        filteredItems.forEach(function(el) { el.classList.remove('d-none'); });
        if (pagWrap) {
            pagWrap.innerHTML = '';
            pagWrap.classList.add('d-none');
        }
        return;
    }

    // Ensure valid current page
    if (currentReviewPage > totalPages) currentReviewPage = totalPages;
    if (currentReviewPage < 1) currentReviewPage = 1;

    var startIdx = (currentReviewPage - 1) * reviewsPerPage;
    var endIdx = startIdx + reviewsPerPage;

    filteredItems.forEach(function(el, idx) {
        if (idx >= startIdx && idx < endIdx) {
            el.classList.remove('d-none');
        } else {
            el.classList.add('d-none');
        }
    });

    // Render Numbered Pagination (Image 2 style: 1 2 > >>|)
    if (pagWrap) {
        pagWrap.classList.remove('d-none');
        var html = '<ul class="psae-pagination-list">';

        for (var p = 1; p <= totalPages; p++) {
            if (p === currentReviewPage) {
                html += '<li class="psae-page-item active" data-page="' + p + '"><span class="psae-page-link">' + p + '</span></li>';
            } else {
                html += '<li class="psae-page-item" data-page="' + p + '"><a href="#" class="psae-page-link">' + p + '</a></li>';
            }
        }

        if (currentReviewPage < totalPages) {
            html += '<li class="psae-page-item" data-page="' + (currentReviewPage + 1) + '"><a href="#" class="psae-page-link" title="Next Page">&rsaquo;</a></li>';
            html += '<li class="psae-page-item" data-page="' + totalPages + '"><a href="#" class="psae-page-link" title="Last Page">&raquo;</a></li>';
        }

        html += '</ul>';
        pagWrap.innerHTML = html;
    }
}

// Initial pagination run after page DOM loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateReviewsPagination);
} else {
    setTimeout(updateReviewsPagination, 100);
}

document.addEventListener('click', function (ev) {
    // 1. Pagination Page Click Event
    var pageItem = ev.target.closest('.psae-page-item');
    if (pageItem && pageItem.hasAttribute('data-page')) {
        ev.preventDefault();
        var targetPage = parseInt(pageItem.getAttribute('data-page'));
        if (targetPage && targetPage !== currentReviewPage) {
            currentReviewPage = targetPage;
            updateReviewsPagination();

            var reviewsSection = document.getElementById('o_product_page_reviews_content');
            if (reviewsSection) {
                reviewsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        return;
    }

    // 2. Dynamic Review Filter Handler (All Reviews, Most Recent, Highest Rating, Lowest Rating)
    var sortItem = ev.target.closest('.psae-filter-bar .dropdown-item');
    if (sortItem) {
        ev.preventDefault();

        var sortType = sortItem.getAttribute('data-sort');
        if (!sortType) return;

        currentReviewFilter = sortType;
        currentReviewPage = 1;

        // Highlight selected item in dropdown menu
        var dropdownMenu = sortItem.closest('.dropdown-menu');
        if (dropdownMenu) {
            dropdownMenu.querySelectorAll('.dropdown-item').forEach(function (el) {
                el.classList.remove('active');
            });
        }
        sortItem.classList.add('active');

        // Update dropdown button label text
        var btn = document.getElementById('psaeReviewSortDropdown');
        if (btn) {
            btn.textContent = sortItem.textContent.trim() + ' ';
        }

        updateReviewsPagination();
    }
});



