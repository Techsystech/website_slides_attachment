/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";

Fullscreen.include({
    /**
     *
     * @private
     * @override
     */
    _renderSlide: function() {
        var def = this._super.apply(this, arguments);
        if (this._renderSlideRunning) { return; }
        this._renderSlideRunning = true;
        try {
            const slide = this._slideValue;
            var $content = this.$('.o_wslides_fs_content');
            if (slide.category === 'video' && slide.videoSourceType === 'local') {
                $content.empty().append(renderToElement('website.slides.fullscreen.content.video', {widget: this}));
                const videoViewer = document.querySelector('#embeddedVideoViewer');
                videoViewer.addEventListener('ended', async (event) => {
                    await this.trigger_up('slide_mark_completed', slide);
                    await this.trigger_up('slide_go_next', slide);
                });
            }
        }
        finally {
            this._renderSlideRunning = false;
        }

        return Promise.all([def]);
    },
});