<template>
  <codemirror :value="content" :options="options"></codemirror>
</template>

<script>
module.exports = {
  props: {
    content: String,
    mode: String
  },
  data () {
    return {
      options: {
        mode: this.mode,
        scrollbarStyle: "simple",
        lineWrapping: true
      }
    }
  }
}
</script>
