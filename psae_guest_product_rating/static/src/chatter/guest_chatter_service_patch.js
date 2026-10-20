import { PortalChatterService } from "@portal/chatter/frontend/portal_chatter_service";
import { patch } from "@web/core/utils/patch";

patch(PortalChatterService.prototype, {
    async initialize(env) {
        const reviewsContent = document.getElementById("o_product_page_reviews_content");
        if (reviewsContent) {
            reviewsContent.classList.add("show");
        }
        const reviewsTitle = document.querySelector(".o_product_page_reviews_title");
        if (reviewsTitle) {
            reviewsTitle.classList.remove("collapsed");
            reviewsTitle.setAttribute("aria-expanded", "true");
        }

        return super.initialize(env);
    }
});
