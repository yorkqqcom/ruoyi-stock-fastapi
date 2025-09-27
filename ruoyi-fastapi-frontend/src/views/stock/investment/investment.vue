<template>
  <div class="html-container">
    <iframe
      :src="htmlFilePath"
      width="100%"
      height="100%"
      frameborder="0"
    ></iframe>
  </div>
</template>

<script>
export default {
  name: 'HTMLViewer',
  data() {
    return {
      htmlFilePath: '/html/investment_report.html'
    }
  }
}
</script>

<style scoped>
.html-container {
  width: 100%;
  height: 100vh;
}
</style>
