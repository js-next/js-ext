<template>
  <div>
    <div v-if="package && !installed">
      <v-alert
        v-if="package && !installed"
        text
        prominent
        class="ma-5"
        border="right"
        type="info"
        icon="mdi-package-variant-closed"
      >
        <span>Package is not installed</span>
        <v-btn
          text
          class="ml-5"
          color="info"
          :loading="installLoading"
          @click.stop="install"
        >Install now</v-btn>
      </v-alert>
    </div>
    <div v-else>
      <v-row v-if="iframeLoading" style="height:100%" align="center" justify="center">
        <v-progress-circular size="100" width="5" color="primary" indeterminate></v-progress-circular>
      </v-row>
      <iframe
        :src="url"
        style="border:none"
        height="100%"
        width="100%"
        @load="iframeLoading = false"
      ></iframe>
    </div>
  </div>
</template>

<script>
module.exports = {
  props: {
    url: String,
    name: String,
    giturl: String,
    package: Boolean
  },
  data() {
    return {
      installed: null,
      iframeLoading: true,
      installLoading: false
    };
  },
  methods: {
    isInstalled() {
      this.$api.packages.getInstalled().then(response => {
        this.installed = JSON.parse(response.data).data.includes(this.name);
      });
    },
    install() {
      this.installLoading = true;
      let promise;

      if (this.giturl) {
        promise = this.$api.packages.add("", this.giturl);
      } else {
        // consider it as an internal package
        promise = this.$api.packages.addInternal(this.name);
      }

      promise
        .then(response => {
          location.reload();
        })
        .catch(error => {
          this.alert(error.message, "error");
        })
        .finally(() => {
          this.installLoading = false;
        });
    }
  },
  mounted() {
    if (this.package) {
      this.isInstalled();
    }
  }
};
</script>
