import { BaseChart } from './base.js';

export class EvalChart extends BaseChart {
    constructor(canvasId) {
        // ID, Label, Color, isPercentage=true
        super(canvasId, 'Win %', '#312e2b', true);
    }

    // You can override update here if you need custom data 
    // transformation specifically for evaluations.
}