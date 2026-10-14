# 分享与留下

## 可以发出去

`可分享/热量账.md`、`可分享/share-card.json`、`可分享/账卡.txt` 只放这些：

- 称号
- 一句说明（规则原文）
- 常点餐品名、单份千卡、出现次数
- 单餐上限
- 数据来源：订单，或自述
- 一句声明：本账只记录热量合计，不是营养或医疗建议

## 留在本地

`ledger.json` 和 `报告.md`。报告里可以有每单的部分合计、待查名称，以及完全可算订单的热量中位。中位不是单餐上限。

## 导出失败

分享稿里出现下面任何一类，`export` 一个文件都不写：

- 订单号、`orderId`
- 门店、`storeName`、`storeCode`
- 地址、小区、号楼、单元、街道
- 11 位手机号
- `Bearer`、`Token`、`MCP_TOKEN`
- 积分加数字、`accumulativePoint`
- `¥`、`￥`、数字加「元」、金额
- 日期、时分秒、下单时间

单餐上限还没确认时也不导出。

归一结果里不允许留下 `orderId`、`storeName`、`storeCode`、`createTime`、`realTotalAmount`、`phone`、`fullAddress`、`address`、`accumulativePoint`、`contactName`。
