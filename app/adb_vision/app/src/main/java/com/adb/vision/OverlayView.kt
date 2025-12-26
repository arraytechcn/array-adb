package com.adb.vision

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View

class OverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val gridCols = 28
    private val gridRows = 4

    private var detections = listOf<RectF>()
    private var shadeInfo = Pair(-1, -1)

    private val gridPaint = Paint().apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 1f
        alpha = 100
    }

    private val shadePaint = Paint().apply {
        color = Color.BLUE
        style = Paint.Style.FILL
        alpha = 150
    }

    private val activePaint = Paint().apply {
        color = Color.GREEN
        style = Paint.Style.FILL
        alpha = 200
    }

    private val detectionPaint = Paint().apply {
        color = Color.RED
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }

    private val textPaint = Paint().apply {
        color = Color.WHITE
        textSize = 24f
        typeface = Typeface.DEFAULT_BOLD
    }

    fun setDetections(objects: List<RectF>, shade: Pair<Int, Int>) {
        detections = objects
        shadeInfo = shade
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val w = width.toFloat()
        val h = height.toFloat()

        // 网格区域 (底部 1/4)
        val gridTop = h * 0.75f
        val gridHeight = h * 0.25f
        val cellWidth = w / gridCols
        val cellHeight = gridHeight / gridRows

        // 绘制 ADB 网格
        for (row in 0 until gridRows) {
            for (col in 0 until gridCols) {
                val left = col * cellWidth
                val top = gridTop + row * cellHeight
                val rect = RectF(left, top, left + cellWidth, top + cellHeight)

                // 判断是否遮蔽
                val isShaded = when {
                    shadeInfo.first >= 0 && col <= shadeInfo.first && row < 2 -> true
                    shadeInfo.second >= 0 && col >= shadeInfo.second && row < 2 -> true
                    else -> false
                }

                // 下两行始终亮
                val isActive = row >= 2 || !isShaded

                canvas.drawRect(rect, if (isActive) activePaint else shadePaint)
                canvas.drawRect(rect, gridPaint)
            }
        }

        // 绘制检测框
        for (det in detections) {
            val rect = RectF(
                det.left * w,
                det.top * h * 0.75f,
                det.right * w,
                det.bottom * h * 0.75f
            )
            canvas.drawRect(rect, detectionPaint)
        }

        // 绘制状态文字
        canvas.drawText("ADB 视觉识别", 20f, 40f, textPaint)
    }
}
