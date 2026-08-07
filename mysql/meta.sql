SET NAMES utf8mb4;
CREATE DATABASE meta DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON meta.* TO 'atguigu'@'%';

USE meta;

DROP TABLE IF EXISTS table_info;
CREATE TABLE `table_info` (
  `id` varchar(64) COLLATE utf8mb4_general_ci NOT NULL COMMENT '表编号',
  `name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '表名称',
  `role` varchar(32) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '表类型(fact/dim)-事实表或维度表',
  `description` text COLLATE utf8mb4_general_ci COMMENT '表描述',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '软删除标记：0未删除 1已删除',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;



DROP TABLE IF EXISTS column_info;
CREATE TABLE `column_info` (
  `id` varchar(64) COLLATE utf8mb4_general_ci NOT NULL COMMENT '列编号',
  `name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '列名称',
  `type` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '数据类型',
  `role` varchar(32) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '列类型(primary_key,foreign_key,measure,dimension)',
  `examples` json DEFAULT NULL COMMENT '数据示例',
  `description` text COLLATE utf8mb4_general_ci COMMENT '列描述',
  `alias` json DEFAULT NULL COMMENT '列别名',
  `table_id` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '所属表编号',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '软删除标记：0未删除 1已删除',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='列信息表';

DROP TABLE IF EXISTS metric_info;
CREATE TABLE `metric_info` (
  `id` varchar(64) COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标编码',
  `name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '指标名称',
  `description` text COLLATE utf8mb4_general_ci COMMENT '指标描述',
  `relevant_columns` json DEFAULT NULL COMMENT '关联的列',
  `alias` json DEFAULT NULL COMMENT '指标别名',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '软删除标记：0未删除 1已删除',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='指标信息表';


DROP TABLE IF EXISTS column_metric;
CREATE TABLE `column_metric` (
  `column_id` varchar(64) COLLATE utf8mb4_general_ci NOT NULL COMMENT '列编号',
  `metric_id` varchar(64) COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标编号',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '软删除标记：0未删除 1已删除',
  PRIMARY KEY (`column_id`,`metric_id`),
  UNIQUE KEY `uk_column_metric` (`column_id`,`metric_id`,`is_deleted`),
  KEY `idx_metric_id` (`metric_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='列与指标关联中间表';




-- 插入数据

INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_customer.customer_id', 'customer_id', 'varchar(20)', 'primary_key', '["C001", "C002", "C003", "C004", "C005", "C006", "C007", "C008", "C009", "C010"]', '客户唯一标识。', '["客户ID", "用户ID"]', 'dim_customer', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_customer.customer_name', 'customer_name', 'varchar(50)', 'dimension', '["李伟", "王芳", "张敏", "刘洋", "陈静", "赵磊", "黄秀英", "吴斌", "周燕", "徐浩"]', '客户名称。', '["客户名称", "用户名称"]', 'dim_customer', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_customer.gender', 'gender', 'varchar(10)', 'dimension', '["男", "女"]', '客户性别。', '["性别"]', 'dim_customer', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_customer.member_level', 'member_level', 'varchar(20)', 'dimension', '["黄金", "白银", "青铜", "铂金"]', '客户会员等级。', '["会员等级", "用户等级"]', 'dim_customer', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_date.date_id', 'date_id', 'int', 'primary_key', '[20250101, 20250102, 20250103, 20250104, 20250105, 20250106, 20250107, 20250108, 20250109, 20250110]', '日期唯一标识，格式 yyyyMMdd。', '["日期ID", "日期"]', 'dim_date', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_date.day', 'day', 'int', 'dimension', '[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]', '日。', '["日", "天"]', 'dim_date', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_date.month', 'month', 'int', 'dimension', '[1, 2, 3]', '月份。', '["月", "月份"]', 'dim_date', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_date.quarter', 'quarter', 'varchar(2)', 'dimension', '["Q1"]', '季度。', '["季度"]', 'dim_date', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_date.year', 'year', 'int', 'dimension', '[2025]', '年份。', '["年", "年份"]', 'dim_date', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_product.brand', 'brand', 'varchar(50)', 'dimension', '["苹果", "三星", "华为", "戴森", "美的", "耐克", "阿迪达斯", "优衣库", "李维斯", "雀巢"]', '商品品牌名称。', '["品牌", "品牌名称"]', 'dim_product', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_product.category', 'category', 'varchar(50)', 'dimension', '["手机数码", "家用电器", "鞋靴", "服饰", "食品饮料", "休闲零食"]', '商品所属品类。', '["商品类别", "品类", "分类"]', 'dim_product', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_product.product_id', 'product_id', 'varchar(20)', 'primary_key', '["P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"]', '商品唯一标识。', '["商品ID", "产品ID"]', 'dim_product', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_product.product_name', 'product_name', 'varchar(200)', 'dimension', '["iPhone 15 Pro", "Galaxy S24 Ultra", "Mate 60 Pro", "戴森 V15 吸尘器", "美的空调 KFR-35GW", "耐克 Air Max 270 运动鞋", "阿迪达斯 Ultraboost 跑鞋", "优衣库 Heattech 保暖夹克", "李维斯 501 牛仔裤", "雀巢金牌速溶咖啡"]', '商品名称。', '["商品名称", "产品名称"]', 'dim_product', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_region.country', 'country', 'varchar(50)', 'dimension', '["中国"]', '地区所属国家名称。', '["国家", "国家名称"]', 'dim_region', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_region.province', 'province', 'varchar(50)', 'dimension', '["广东省", "浙江省", "四川省", "北京市", "上海市", "湖北省"]', '订单所属的省份名称。', '["省份", "省", "所在省份"]', 'dim_region', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_region.region_id', 'region_id', 'varchar(20)', 'primary_key', '["R001", "R002", "R003", "R004", "R005", "R006"]', '地区唯一标识。', '["地区ID", "区域ID"]', 'dim_region', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('dim_region.region_name', 'region_name', 'varchar(50)', 'dimension', '["华南", "华东", "西南", "华北", "华中"]', '订单所属的大区名称，如华东、华南等。', '["地区", "区域", "大区"]', 'dim_region', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.customer_id', 'customer_id', 'varchar(20)', 'foreign_key', '["C001", "C005", "C003", "C008", "C012", "C015", "C002", "C007", "C010", "C019"]', '关联客户维度的外键。', '["客户ID", "用户ID"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.date_id', 'date_id', 'int', 'foreign_key', '[20250101, 20250102, 20250103, 20250104, 20250105, 20250106, 20250107, 20250108, 20250109, 20250110]', '关联时间维度的外键。', '["日期", "下单日期"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.order_amount', 'order_amount', 'float', 'measure', '[8999.0, 6999.0, 125.0, 899.0, 60.0, 1399.0, 40.0, 299.0, 200.0, 9499.0]', '订单金额。', '["销售额", "订单金额", "收入"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.order_id', 'order_id', 'varchar(30)', 'primary_key', '["ORD20250101001", "ORD20250101002", "ORD20250102001", "ORD20250102002", "ORD20250103001", "ORD20250103002", "ORD20250104001", "ORD20250105001", "ORD20250105002", "ORD20250106001"]', '订单唯一标识。', '["订单ID"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.order_quantity', 'order_quantity', 'int', 'measure', '[1, 5, 12, 8, 2, 10, 3, 6, 25, 4]', '订单中商品的购买数量。', '["销量", "购买数量", "件数"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.product_id', 'product_id', 'varchar(20)', 'foreign_key', '["P001", "P003", "P010", "P006", "P011", "P014", "P012", "P008", "P002", "P013"]', '关联商品维度的外键。', '["商品ID", "产品ID"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);
INSERT INTO meta.column_info
(id, name, `type`, `role`, examples, description, alias, table_id, created_at, updated_at, is_deleted)
VALUES('fact_order.region_id', 'region_id', 'varchar(20)', 'foreign_key', '["R001", "R005", "R002", "R004", "R003", "R006"]', '关联地区维度的外键。', '["地区ID", "区域ID"]', 'fact_order', '2026-08-04 05:49:58', '2026-08-04 05:49:58', 0);




INSERT INTO meta.metric_info
(id, name, description, relevant_columns, alias, created_at, updated_at, is_deleted)
VALUES('AOV', 'AOV', '全称Average Order Value，表示所有订单的成交金额平均值。', '["fact_order.order_quantity"]', '["平均单价", "平均订单金额"]', '2026-08-04 05:51:01', '2026-08-04 05:51:01', 0);
INSERT INTO meta.metric_info
(id, name, description, relevant_columns, alias, created_at, updated_at, is_deleted)
VALUES('GMV', 'GMV', '全称Gross Merchandise Value，表示所有订单的成交金额总和。', '["fact_order.order_amount"]', '["成交总额", "订单总额"]', '2026-08-04 05:51:01', '2026-08-04 05:51:01', 0);



INSERT INTO meta.metric_info
(id, name, description, relevant_columns, alias, created_at, updated_at, is_deleted)
VALUES('AOV', 'AOV', '全称Average Order Value，表示所有订单的成交金额平均值。', '["fact_order.order_quantity"]', '["平均单价", "平均订单金额"]', '2026-08-04 05:51:01', '2026-08-04 05:51:01', 0);
INSERT INTO meta.metric_info
(id, name, description, relevant_columns, alias, created_at, updated_at, is_deleted)
VALUES('GMV', 'GMV', '全称Gross Merchandise Value，表示所有订单的成交金额总和。', '["fact_order.order_amount"]', '["成交总额", "订单总额"]', '2026-08-04 05:51:01', '2026-08-04 05:51:01', 0);


INSERT INTO meta.table_info
(id, name, `role`, description, created_at, updated_at, is_deleted)
VALUES('dim_customer', 'dim_customer', 'dim', '客户维度表，描述下单客户的基本属性。', NULL, NULL, 0);
INSERT INTO meta.table_info
(id, name, `role`, description, created_at, updated_at, is_deleted)
VALUES('dim_date', 'dim_date', 'dim', '时间维度表，用于多时间粒度分析。', NULL, NULL, 0);
INSERT INTO meta.table_info
(id, name, `role`, description, created_at, updated_at, is_deleted)
VALUES('dim_product', 'dim_product', 'dim', '商品维度表，描述商品的基本属性信息。', NULL, NULL, 0);
INSERT INTO meta.table_info
(id, name, `role`, description, created_at, updated_at, is_deleted)
VALUES('dim_region', 'dim_region', 'dim', '地区维度表，用于描述订单发生的地理区域信息。', NULL, NULL, 0);
INSERT INTO meta.table_info
(id, name, `role`, description, created_at, updated_at, is_deleted)
VALUES('fact_order', 'fact_order', 'fact', '订单事实表，记录订单数量和金额等核心指标。', NULL, NULL, 0);