package com.adb.vision

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.*
import android.os.Bundle
import android.util.Log
import android.util.Size
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.adb.vision.databinding.ActivityMainBinding
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.objects.ObjectDetection
import com.google.mlkit.vision.objects.defaults.ObjectDetectorOptions
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var cameraExecutor: ExecutorService

    // ADB 网格参数 (28列 x 4行)
    private val gridCols = 28
    private val gridRows = 4

    // 检测到的目标
    private var detectedObjects = mutableListOf<RectF>()

    // ML Kit 目标检测器
    private val objectDetector by lazy {
        val options = ObjectDetectorOptions.Builder()
            .setDetectorMode(ObjectDetectorOptions.STREAM_MODE)
            .enableMultipleObjects()
            .build()
        ObjectDetection.getClient(options)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS)
        }

        cameraExecutor = Executors.newSingleThreadExecutor()
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder()
                .setTargetResolution(Size(1280, 720))
                .build()
                .also {
                    it.setSurfaceProvider(binding.viewFinder.surfaceProvider)
                }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setTargetResolution(Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalyzer)
            } catch (e: Exception) {
                Log.e(TAG, "相机绑定失败", e)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun processImage(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run {
            imageProxy.close()
            return
        }

        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        objectDetector.process(image)
            .addOnSuccessListener { objects ->
                detectedObjects.clear()

                for (obj in objects) {
                    val box = obj.boundingBox
                    // 转换为相对坐标 (0-1)
                    val rect = RectF(
                        box.left.toFloat() / image.width,
                        box.top.toFloat() / image.height,
                        box.right.toFloat() / image.width,
                        box.bottom.toFloat() / image.height
                    )
                    detectedObjects.add(rect)
                }

                // 计算 ADB 遮蔽区域
                val shadeInfo = calculateShadeColumns()

                runOnUiThread {
                    binding.overlayView.setDetections(detectedObjects, shadeInfo)
                    binding.statusText.text = "检测: ${detectedObjects.size} | 左遮蔽: ${shadeInfo.first} | 右遮蔽: ${shadeInfo.second}"
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "检测失败", e)
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }

    // 计算遮蔽列 (返回 左起始列, 右结束列)
    private fun calculateShadeColumns(): Pair<Int, Int> {
        if (detectedObjects.isEmpty()) {
            return Pair(-1, -1) // 无遮蔽
        }

        var leftShade = gridCols
        var rightShade = -1

        for (rect in detectedObjects) {
            // 目标中心 X 坐标
            val centerX = (rect.left + rect.right) / 2

            // 映射到网格列
            val col = (centerX * gridCols).toInt().coerceIn(0, gridCols - 1)

            // 根据目标位置决定遮蔽方向
            if (centerX < 0.5f) {
                // 左半边目标 -> 从左边遮蔽
                leftShade = minOf(leftShade, col)
            } else {
                // 右半边目标 -> 从右边遮蔽
                rightShade = maxOf(rightShade, col)
            }
        }

        return Pair(
            if (leftShade < gridCols) leftShade else -1,
            if (rightShade >= 0) rightShade else -1
        )
    }

    private fun allPermissionsGranted() = REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(baseContext, it) == PackageManager.PERMISSION_GRANTED
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera()
            } else {
                Toast.makeText(this, "需要相机权限", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }

    companion object {
        private const val TAG = "ADBVision"
        private const val REQUEST_CODE_PERMISSIONS = 10
        private val REQUIRED_PERMISSIONS = arrayOf(Manifest.permission.CAMERA)
    }
}
