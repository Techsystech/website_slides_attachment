/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { SlideUploadCategory } from "@website_slides/js/public/components/slide_upload_dialog/slide_upload_category";
import { SlideUploadDialog } from "@website_slides/js/public/components/slide_upload_dialog/slide_upload_dialog";

patch(SlideUploadDialog.prototype, {
    setup() {
        super.setup();
        this.pagesTemplates.local_video = "website_slides_attachment.SlideCategoryTutorial.LocalVideo";
        this.slideCategoryData.local_video = {
            icon: "fa-file-video-o",
            label: _t("Local Video"),
        };
    },

    onClickSlideCategoryIcon(slideCategory) {
        super.onClickSlideCategoryIcon(slideCategory);
        if (slideCategory === "local_video") {
            this.state.title = _t("Add Local Video");
        }
    },

    async uploadSlide(formValues, previousPage) {
        if (previousPage !== "local_video") {
            return super.uploadSlide(formValues, previousPage);
        }
        this.state.page = "upload";
        this.state.size = "md";

        const body = new FormData();
        for (const [key, value] of Object.entries(formValues)) {
            if (value === undefined || value === null) {
                continue;
            }
            const fieldValue = typeof value === "object" && !(value instanceof File)
                ? JSON.stringify(value)
                : value;
            body.append(key, fieldValue);
        }
        if (odoo.csrf_token) {
            body.append("csrf_token", odoo.csrf_token);
        }

        const response = await fetch("/website_slides_attachment/add_local_video_slide", {
            method: "POST",
            body,
            credentials: "same-origin",
        });
        const data = await response.json();
        if (!response.ok || data.error) {
            this.state.page = previousPage;
            this.state.size = "lg";
            this.state.alertMsg = data.error || _t("Upload failed. Please try again.");
            return;
        }
        window.location = data.url;
    },
});

patch(SlideUploadCategory.prototype, {
    setup() {
        super.setup();
        this.sourceSettings.local_video = {
            sourceTypeLabel: _t("Video Source"),
            selectFileLabel: _t("Choose a Video"),
            acceptedFiles: "video/*,.mp4,.mov,.webm,.m4v",
            localOnly: true,
        };
    },

    async onChangeFileInput(ev) {
        if (this.props.slideCategory !== "local_video") {
            return super.onChangeFileInput(ev);
        }
        this._alertRemove();
        const file = ev.target.files[0];
        if (!file) {
            this.file = {};
            this.state.preview.show = false;
            return;
        }
        if (!/^video\/.*/.test(file.type) && !/\.(mp4|mov|m4v|webm)$/i.test(file.name)) {
            this._alertDisplay(_t("Invalid file type. Please select a video file."));
            this._fileReset();
            this.state.preview.show = false;
            return;
        }
        this.file.name = file.name;
        this.file.type = file.type || "video/mp4";
        this.file.file = file;
        if (!this.state.form.slideName) {
            this.state.form.slideName = file.name.replace(/\.[^.]+$/, "");
        }
        this.state.preview.videoTitle = file.name;
        this.state.preview.hideSlideVideoTitle = false;
        this.state.preview.show = true;
    },

    _formValidateGetValues(forcePublished) {
        if (this.props.slideCategory !== "local_video") {
            return super._formValidateGetValues(forcePublished);
        }
        return Object.assign({
            channel_id: this.props.channelId,
            duration: this.state.form.duration,
            file_name: this.file.name,
            file_type: this.file.type,
            is_published: forcePublished,
            local_video_file: this.file.file,
            name: this.state.form.slideName,
        }, this._getSelectMenuValues());
    },
});
