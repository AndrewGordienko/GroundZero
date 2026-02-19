import { BaseChart } from './base.js';

export class DepthChart extends BaseChart {
    constructor(canvasId) {
        // ID, Label, Color, isPercentage=false
        super(canvasId, 'Depth', '#2196f3', false);
    }
}