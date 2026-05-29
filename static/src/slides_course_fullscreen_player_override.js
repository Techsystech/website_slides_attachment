/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";

Fullscreen.include({
    /**
     * Render local / nextcloud video slides in fullscreen using a native <video> element.
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
        // For local / nextcloud videos it renders nothing, so we fill the content here.
        const isLocal = slide.videoSourceType === 'local' || slide.isLocalVideo;
        const isNextcloud = slide.videoSourceType === 'nextcloud';
        if (!isLocal && !isNextcloud) {
            return def;
        }

        // Build the download URL in JS because encodeURIComponent is not
        // available inside OWL template expressions (ctx.encodeURIComponent).
        var filename = (slide.name || 'local-video') + '.mp4';
        this._localVideoSrc = '/website_slides_attachment/download/' + slide.id +
                              '/filename=' + encodeURIComponent(filename);
        this._localVideoMimeType = slide.videoAttachmentMimetype || slide.video_attachment_mimetype || 'video/mp4';

        var $content = this.$('.o_wslides_fs_content');
        $content.empty().append(renderToElement('website.slides.fullscreen.content.video', {widget: this}));

        const videoViewer = document.querySelector('#embeddedVideoViewer');
        if (videoViewer) {
            if (this._localVideoEndedHandler) {
                videoViewer.removeEventListener('ended', this._localVideoEndedHandler);
            }
            this._localVideoEndedHandler = async (event) => {
                await this.trigger_up('slide_mark_completed', slide);
                await this.trigger_up('slide_go_next', slide);
            };
            videoViewer.addEventListener('ended', this._localVideoEndedHandler);
        }

        return def;
    },
});