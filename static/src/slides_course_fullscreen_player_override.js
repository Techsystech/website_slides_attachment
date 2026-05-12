/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";

Fullscreen.include({
    /**
     * Render local video slides in fullscreen using a native <video> element.
     *
     * @private
     * @override
     */
    _renderSlide: async function () {
        // Let the base handle quiz / standard video types first.
        var def = await this._super.apply(this, arguments);

        const slide = this._slideValue;
        if (slide.category !== 'video') {
            return def;
        }

        // The base method only knows youtube / vimeo / google_drive.
        // For local videos it renders nothing, so we fill the content here.
        const isLocal = slide.videoSourceType === 'local' || slide.isLocalVideo;
        if (!isLocal) {
            return def;
        }

        // Build the download URL in JS because encodeURIComponent is not
        // available inside OWL template expressions (ctx.encodeURIComponent).
        var filename = (slide.name || 'local-video') + '.mp4';
        this._localVideoSrc = '/website_slides_attachment/download/' + slide.id +
                              '/filename=' + encodeURIComponent(filename);

        var $content = this.$('.o_wslides_fs_content');
        $content.empty().append(renderToElement('website.slides.fullscreen.content.video', {widget: this}));

        const videoViewer = document.querySelector('#embeddedVideoViewer');
        if (videoViewer) {
            videoViewer.addEventListener('ended', async (event) => {
                await this.trigger_up('slide_mark_completed', slide);
                await this.trigger_up('slide_go_next', slide);
            });
        }

        return def;
    },
});