<template>
  <v-container>
    <v-row v-if="loading" style="height:100%" align="center" justify="center">
      <v-progress-circular size="100" width="5" color="primary" indeterminate></v-progress-circular>
    </v-row>
    <!-- <vue-simple-markdown v-else :source="source" :emoji="false"></vue-simple-markdown> -->
    <div v-html="source"></div>
  </v-container>
</template>

<script>
module.exports = {
  data() {
    return {
      source: "",
      loading: true
    };
  },
  props: {
    url: String,
    baseUrl: String
  },
  mounted() {
    this.loading = true;
    this.$root.$emit("sidebar", true);
    this.$api.content.get(this.url).then(res => {
      let options = {};
      if (this.baseUrl) {
        options.baseUrl = this.baseUrl;
      }
      this.source = marked(res.data, options);
      this.loading = false;
    });
  }
};
</script>
