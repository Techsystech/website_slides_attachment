/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

Fullscreen.include({
    /**
     *
     * @private
     * @override
     */
    _renderSlide: async function() {
        var def = this._super.apply(this, arguments);
        if (this._renderSlideRunning) { return; }
        this._renderSlideRunning = true;
        try {
            const slide = this._slideValue;
            var $content = this.$('.o_wslides_fs_content');
            if (slide.category === 'video' && slide.videoSourceType === 'local') {
                $content.empty().append(renderToElement('website.slides.fullscreen.content.video', {widget: this}));
                const videoViewer = document.querySelector('#embeddedVideoViewer')
                videoViewer.addEventListener('ended', (event) => {
                    this.trigger_up('slide_mark_completed', slide);
                    this.trigger_up('slide_go_next', slide);
                });
            }
        }
        finally {
            this._renderSlideRunning = false;
        }

        return Promise.all([def])
    },
});