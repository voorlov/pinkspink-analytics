// ============================================================
// Ping Spinning — GA4 Analytics + Facebook Ads Dashboard
// ============================================================
// GA4 Property ID: 411715710
// Spreadsheet ID: 1BJlK5UDgikDzszMFnrIFKtnvqoiTefgpvqkRieAbciw
// ============================================================

const GA4_PROPERTY_ID = '411715710';

// Страны для исключения из всех отчётов (ваш собственный трафик)
const EXCLUDED_COUNTRIES = ['China', 'Hong Kong'];

// Период по умолчанию — 30 дней
const DEFAULT_DAYS = 30;

// ============================================================
// МЕНЮ
// ============================================================

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('GA4 Analytics')
    .addItem('Update All', 'updateAll')
    .addSeparator()
    .addItem('Daily Overview', 'updateDailyOverview')
    .addItem('E-commerce KPIs', 'updateEcommerceKPIs')
    .addItem('Traffic Sources', 'updateTrafficSources')
    .addItem('Top Products', 'updateTopProducts')
    .addItem('Top Pages', 'updateTopPages')
    .addItem('Devices & Geo', 'updateDevicesGeo')
    .addItem('Retention', 'updateRetention')
    .addSeparator()
    .addItem('Facebook Ads', 'updateFacebookAds')
    .addItem('Ad Performance (GA4 + FB)', 'updateAdPerformance')
    .addSeparator()
    .addItem('Setup Facebook Token', 'promptFacebookSetup')
    .addItem('Create Daily Trigger', 'createDailyTrigger')
    .addToUi();
}

// ============================================================
// ТРИГГЕР
// ============================================================

function createDailyTrigger() {
  // Удаляем старые триггеры
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'updateAll') {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger('updateAll')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();

  SpreadsheetApp.getUi().alert('Триггер создан: ежедневное обновление в 6:00');
}

// ============================================================
// UPDATE ALL
// ============================================================

function updateAll() {
  updateDailyOverview();
  updateEcommerceKPIs();
  updateTrafficSources();
  updateTopProducts();
  updateTopPages();
  updateDevicesGeo();
  updateRetention();

  // Facebook Ads — только если настроен токен
  const props = PropertiesService.getScriptProperties();
  if (props.getProperty('FB_ACCESS_TOKEN') && props.getProperty('FB_AD_ACCOUNT_ID')) {
    updateFacebookAds();
    updateAdPerformance();
  }
}

// ============================================================
// УТИЛИТЫ
// ============================================================

function getDateRange(days) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - (days || DEFAULT_DAYS));
  return {
    startDate: Utilities.formatDate(start, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
    endDate: Utilities.formatDate(end, Session.getScriptTimeZone(), 'yyyy-MM-dd')
  };
}

/**
 * Создаёт фильтр, исключающий заданные страны.
 */
function getCountryExclusionFilter() {
  return {
    notExpression: {
      filter: {
        fieldName: 'country',
        inListFilter: {
          values: EXCLUDED_COUNTRIES
        }
      }
    }
  };
}

/**
 * Комбинирует фильтр исключения стран с дополнительным фильтром через andGroup.
 */
function combineFilters(additionalFilter) {
  if (!additionalFilter) {
    return getCountryExclusionFilter();
  }
  return {
    andGroup: {
      expressions: [
        getCountryExclusionFilter(),
        additionalFilter
      ]
    }
  };
}

/**
 * Выполняет запрос к GA4 Data API.
 */
function runGA4Report(request) {
  const dates = getDateRange();

  const body = {
    dateRanges: [{ startDate: dates.startDate, endDate: dates.endDate }],
    dimensions: request.dimensions.map(d => ({ name: d })),
    metrics: request.metrics.map(m => ({ name: m })),
    dimensionFilter: combineFilters(request.dimensionFilter || null),
    orderBys: request.orderBys || [],
    limit: request.limit || 10000
  };

  const url = `https://analyticsdata.googleapis.com/v1beta/properties/${GA4_PROPERTY_ID}:runReport`;
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + ScriptApp.getOAuthToken()
    },
    payload: JSON.stringify(body),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  const result = JSON.parse(response.getContentText());

  if (result.error) {
    throw new Error(`GA4 API Error: ${result.error.message}`);
  }

  return result;
}

/**
 * Записывает данные на лист таблицы.
 */
function writeToSheet(sheetName, headers, rows) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }

  sheet.clearContents();

  if (rows.length === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    return sheet;
  }

  const data = [headers, ...rows];
  sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');

  // Автоширина колонок
  for (let i = 1; i <= headers.length; i++) {
    sheet.autoResizeColumn(i);
  }

  return sheet;
}

/**
 * Извлекает строки из ответа GA4 API.
 */
function extractRows(result) {
  if (!result.rows) return [];
  return result.rows.map(row => {
    const dims = row.dimensionValues.map(d => d.value);
    const mets = row.metricValues.map(m => m.value);
    return [...dims, ...mets];
  });
}

/**
 * Форматирует число как валюту.
 */
function fmtCurrency(val) {
  const num = parseFloat(val) || 0;
  return '$' + num.toFixed(0);
}

/**
 * Форматирует как процент.
 */
function fmtPercent(val) {
  const num = parseFloat(val) || 0;
  return (num * 100).toFixed(1) + '%';
}

// ============================================================
// 1. DAILY OVERVIEW
// ============================================================

function updateDailyOverview() {
  const result = runGA4Report({
    dimensions: ['date'],
    metrics: [
      'sessions', 'totalUsers', 'newUsers',
      'engagementRate', 'userEngagementDuration',
      'screenPageViews', 'purchaseRevenue', 'ecommercePurchases'
    ],
    orderBys: [{ dimension: { dimensionName: 'date' }, desc: false }]
  });

  const headers = [
    'Дата', 'Сессии', 'Пользователи', 'Новые пользователи',
    'Engagement Rate', 'Время вовлечения (сек)', 'Просмотры страниц',
    'Доход', 'Покупки'
  ];

  const rows = extractRows(result).map(r => {
    // Форматируем дату YYYYMMDD -> YYYY-MM-DD
    const d = r[0];
    const dateStr = d.substring(0, 4) + '-' + d.substring(4, 6) + '-' + d.substring(6, 8);
    return [
      dateStr,
      parseInt(r[1]),
      parseInt(r[2]),
      parseInt(r[3]),
      fmtPercent(r[4]),
      parseInt(parseFloat(r[5])),
      parseInt(r[6]),
      fmtCurrency(r[7]),
      parseInt(r[8])
    ];
  });

  writeToSheet('Daily Overview', headers, rows);
}

// ============================================================
// 2. E-COMMERCE KPIs
// ============================================================

function updateEcommerceKPIs() {
  const result = runGA4Report({
    dimensions: ['date'],
    metrics: [
      'purchaseRevenue', 'ecommercePurchases', 'averagePurchaseRevenue',
      'addToCarts', 'checkouts', 'ecommercePurchases',
      'sessionConversionRate', 'cartToViewRate'
    ],
    orderBys: [{ dimension: { dimensionName: 'date' }, desc: false }],
    // Показываем только дни с какой-либо e-commerce активностью
    dimensionFilter: null
  });

  const headers = [
    'Дата', 'Доход', 'Транзакции', 'Средний чек (AOV)',
    'Добавл. в корзину', 'Начало оформления', 'Покупки',
    'Конверсия', 'Cart Abandonment Rate'
  ];

  const rows = extractRows(result)
    .filter(r => {
      // Показываем только дни с активностью воронки
      return parseFloat(r[4]) > 0 || parseFloat(r[5]) > 0 || parseFloat(r[6]) > 0;
    })
    .map(r => {
      const d = r[0];
      const dateStr = d.substring(0, 4) + '-' + d.substring(4, 6) + '-' + d.substring(6, 8);
      const addToCart = parseInt(r[4]);
      const purchases = parseInt(r[6]);
      const cartAbandonment = addToCart > 0 && purchases === 0 ? '100.0%'
        : addToCart > 0 ? ((1 - purchases / addToCart) * 100).toFixed(1) + '%' : '';

      return [
        dateStr,
        fmtCurrency(r[1]),
        parseInt(r[2]),
        fmtCurrency(r[3]),
        addToCart,
        parseInt(r[5]),
        purchases,
        fmtPercent(r[7]),
        cartAbandonment
      ];
    });

  writeToSheet('E-commerce KPIs', headers, rows);
}

// ============================================================
// 3. TRAFFIC SOURCES
// ============================================================

function updateTrafficSources() {
  // Часть 1: По каналам
  const channelResult = runGA4Report({
    dimensions: ['sessionDefaultChannelGroup'],
    metrics: ['sessions', 'totalUsers', 'engagementRate', 'ecommercePurchases', 'purchaseRevenue'],
    orderBys: [{ metric: { metricName: 'sessions' }, desc: true }]
  });

  const channelHeaders = ['Канал', 'Сессии', 'Пользователи', 'Engagement Rate', 'Покупки', 'Доход'];
  const channelRows = extractRows(channelResult).map(r => [
    r[0], parseInt(r[1]), parseInt(r[2]), fmtPercent(r[3]), parseInt(r[4]), fmtCurrency(r[5])
  ]);

  // Часть 2: Source / Medium
  const sourceResult = runGA4Report({
    dimensions: ['sessionSource', 'sessionMedium'],
    metrics: ['sessions', 'totalUsers', 'engagementRate', 'ecommercePurchases', 'purchaseRevenue'],
    orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
    limit: 20
  });

  const sourceRows = extractRows(sourceResult).map(r => [
    r[0], r[1], parseInt(r[2]), parseInt(r[3]), fmtPercent(r[4]), fmtCurrency(r[6])
  ]);

  // Записываем обе таблицы на один лист
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('Traffic Sources');
  if (!sheet) sheet = ss.insertSheet('Traffic Sources');
  sheet.clearContents();

  // Каналы
  const channelData = [channelHeaders, ...channelRows];
  sheet.getRange(1, 1, channelData.length, channelData[0].length).setValues(channelData);
  sheet.getRange(1, 1, 1, channelHeaders.length).setFontWeight('bold');

  // Разделитель
  const separatorRow = channelData.length + 2;
  sheet.getRange(separatorRow, 1).setValue('Source / Medium');
  sheet.getRange(separatorRow, 1).setFontWeight('bold');

  // Source/Medium заголовки
  const smHeaders = ['Source', 'Medium', 'Сессии', 'Пользователи', 'Engagement Rate', 'Доход'];
  const smStart = separatorRow + 1;
  const smData = [smHeaders, ...sourceRows];
  sheet.getRange(smStart, 1, smData.length, smData[0].length).setValues(smData);
  sheet.getRange(smStart, 1, 1, smHeaders.length).setFontWeight('bold');

  for (let i = 1; i <= 6; i++) sheet.autoResizeColumn(i);
}

// ============================================================
// 4. TOP PRODUCTS (Item-scoped)
// ============================================================

function updateTopProducts() {
  const result = runGA4Report({
    dimensions: ['itemName'],
    metrics: [
      'itemsViewed', 'itemsAddedToCart', 'itemsCheckedOut',
      'itemsPurchased', 'itemRevenue'
    ],
    orderBys: [{ metric: { metricName: 'itemsViewed' }, desc: true }],
    limit: 50,
    // Item-scoped запросы не поддерживают обычные dimension filters на country,
    // поэтому убираем country filter для этого запроса
    dimensionFilter: null
  });

  const headers = [
    'Product', 'Views', 'Added to Cart', 'Checked Out',
    'Purchased', 'Revenue', 'View-to-Cart Rate'
  ];

  const rows = extractRows(result).map(r => {
    const views = parseInt(r[1]);
    const addToCart = parseInt(r[2]);
    const viewToCart = views > 0 ? ((addToCart / views) * 100).toFixed(1) + '%' : '0.0%';
    return [
      r[0], views, addToCart, parseInt(r[3]),
      parseInt(r[4]), fmtCurrency(r[5]), viewToCart
    ];
  });

  writeToSheet('Top Products', headers, rows);
}

// ============================================================
// 5. TOP PAGES
// ============================================================

function updateTopPages() {
  const result = runGA4Report({
    dimensions: ['pagePath'],
    metrics: [
      'screenPageViews', 'totalUsers', 'engagementRate',
      'ecommercePurchases', 'purchaseRevenue'
    ],
    orderBys: [{ metric: { metricName: 'screenPageViews' }, desc: true }],
    limit: 50
  });

  const headers = ['Page', 'Views', 'Users', 'Engagement Rate', 'Purchases', 'Revenue'];

  const rows = extractRows(result).map(r => [
    r[0], parseInt(r[1]), parseInt(r[2]),
    fmtPercent(r[3]), parseInt(r[4]), fmtCurrency(r[5])
  ]);

  writeToSheet('Top Pages', headers, rows);
}

// ============================================================
// 6. DEVICES & GEO
// ============================================================

function updateDevicesGeo() {
  // Устройства
  const deviceResult = runGA4Report({
    dimensions: ['deviceCategory'],
    metrics: ['sessions', 'totalUsers', 'engagementRate', 'ecommercePurchases', 'purchaseRevenue'],
    orderBys: [{ metric: { metricName: 'sessions' }, desc: true }]
  });

  const deviceRows = extractRows(deviceResult).map(r => [
    r[0], parseInt(r[1]), parseInt(r[2]), fmtPercent(r[3]), parseInt(r[4]), fmtCurrency(r[5])
  ]);

  // Страны (тоже с фильтром — исключаем Китай/ГК)
  const geoResult = runGA4Report({
    dimensions: ['country'],
    metrics: ['sessions', 'totalUsers', 'engagementRate', 'ecommercePurchases', 'purchaseRevenue'],
    orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
    limit: 20
  });

  const geoRows = extractRows(geoResult).map(r => [
    r[0], parseInt(r[1]), parseInt(r[2]), fmtPercent(r[3]), parseInt(r[4]), fmtCurrency(r[5])
  ]);

  // Записываем на один лист
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('Devices & Geo');
  if (!sheet) sheet = ss.insertSheet('Devices & Geo');
  sheet.clearContents();

  const headers = ['Device', 'Sessions', 'Users', 'Engagement Rate', 'Purchases', 'Revenue'];
  const devData = [headers, ...deviceRows];
  sheet.getRange(1, 1, devData.length, devData[0].length).setValues(devData);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');

  const geoStart = devData.length + 2;
  sheet.getRange(geoStart, 1).setValue('Geography');
  sheet.getRange(geoStart, 1).setFontWeight('bold');

  const geoHeaders = ['Country', 'Sessions', 'Users', 'Engagement Rate', 'Purchases', 'Revenue'];
  const geoData = [geoHeaders, ...geoRows];
  sheet.getRange(geoStart + 1, 1, geoData.length, geoData[0].length).setValues(geoData);
  sheet.getRange(geoStart + 1, 1, 1, geoHeaders.length).setFontWeight('bold');

  for (let i = 1; i <= 6; i++) sheet.autoResizeColumn(i);
}

// ============================================================
// 7. RETENTION
// ============================================================

function updateRetention() {
  const result = runGA4Report({
    dimensions: ['newVsReturning'],
    metrics: [
      'totalUsers', 'sessions', 'purchaseRevenue',
      'ecommercePurchases', 'engagementRate'
    ],
    orderBys: [{ metric: { metricName: 'totalUsers' }, desc: true }]
  });

  const headers = ['User Type', 'Users', 'Sessions', 'Revenue', 'Purchases', 'Engagement Rate'];

  const rows = extractRows(result).map(r => [
    r[0], parseInt(r[1]), parseInt(r[2]),
    fmtCurrency(r[3]), parseInt(r[4]), fmtPercent(r[5])
  ]);

  writeToSheet('Retention', headers, rows);
}


// ============================================================
// FACEBOOK MARKETING API INTEGRATION
// ============================================================

/**
 * Диалог настройки Facebook токена и Ad Account ID.
 */
function promptFacebookSetup() {
  const ui = SpreadsheetApp.getUi();

  const tokenResponse = ui.prompt(
    'Facebook Setup (1/2)',
    'Вставьте Long-Lived Access Token из Facebook:\n\n' +
    '(Получить: developers.facebook.com → Marketing API → Tools → Access Token)',
    ui.ButtonSet.OK_CANCEL
  );
  if (tokenResponse.getSelectedButton() !== ui.Button.OK) return;

  const accountResponse = ui.prompt(
    'Facebook Setup (2/2)',
    'Введите Ad Account ID (без "act_" префикса):\n\n' +
    '(Найти: Business Settings → Ad Accounts → ID)',
    ui.ButtonSet.OK_CANCEL
  );
  if (accountResponse.getSelectedButton() !== ui.Button.OK) return;

  const props = PropertiesService.getScriptProperties();
  props.setProperty('FB_ACCESS_TOKEN', tokenResponse.getResponseText().trim());
  props.setProperty('FB_AD_ACCOUNT_ID', accountResponse.getResponseText().trim());

  ui.alert('Facebook настроен! Теперь можно использовать "Facebook Ads" и "Ad Performance".');
}

/**
 * Вызов Facebook Marketing API.
 */
function callFacebookAPI(endpoint, params) {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('FB_ACCESS_TOKEN');
  const accountId = props.getProperty('FB_AD_ACCOUNT_ID');

  if (!token || !accountId) {
    throw new Error('Facebook не настроен. Используйте меню: GA4 Analytics → Setup Facebook Token');
  }

  const baseUrl = `https://graph.facebook.com/v21.0/act_${accountId}/${endpoint}`;
  const queryParams = Object.entries({ ...params, access_token: token })
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');

  const url = `${baseUrl}?${queryParams}`;
  const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  const result = JSON.parse(response.getContentText());

  if (result.error) {
    throw new Error(`Facebook API Error: ${result.error.message}`);
  }

  return result;
}

/**
 * Получает данные из Facebook Ads по дням.
 */
function getFacebookAdsData() {
  const dates = getDateRange();

  const result = callFacebookAPI('insights', {
    time_range: JSON.stringify({
      since: dates.startDate,
      until: dates.endDate
    }),
    time_increment: 1, // по дням
    fields: [
      'date_start',
      'campaign_name',
      'impressions',
      'reach',
      'clicks',
      'cpc',
      'cpm',
      'ctr',
      'spend',
      'actions',
      'cost_per_action_type'
    ].join(','),
    level: 'campaign',
    limit: 500
  });

  return result.data || [];
}

/**
 * Обновляет вкладку Facebook Ads.
 */
function updateFacebookAds() {
  const data = getFacebookAdsData();

  const headers = [
    'Дата', 'Кампания', 'Показы', 'Охват', 'Клики',
    'CPC', 'CPM', 'CTR', 'Расход', 'Результаты', 'Цена за результат'
  ];

  const rows = data.map(row => {
    // Извлекаем ключевые действия (link_clicks, landing_page_view и т.д.)
    const actions = row.actions || [];
    const linkClicks = actions.find(a => a.action_type === 'link_click');
    const resultCount = linkClicks ? parseInt(linkClicks.value) : 0;

    const costPerAction = row.cost_per_action_type || [];
    const costPerClick = costPerAction.find(a => a.action_type === 'link_click');
    const resultCost = costPerClick ? '$' + parseFloat(costPerClick.value).toFixed(2) : '-';

    return [
      row.date_start,
      row.campaign_name || '(no name)',
      parseInt(row.impressions || 0),
      parseInt(row.reach || 0),
      parseInt(row.clicks || 0),
      '$' + parseFloat(row.cpc || 0).toFixed(2),
      '$' + parseFloat(row.cpm || 0).toFixed(2),
      parseFloat(row.ctr || 0).toFixed(2) + '%',
      '$' + parseFloat(row.spend || 0).toFixed(2),
      resultCount,
      resultCost
    ];
  });

  // Сортируем по дате
  rows.sort((a, b) => a[0].localeCompare(b[0]));

  writeToSheet('Facebook Ads', headers, rows);

  // Добавляем итоговую строку
  if (rows.length > 0) {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Facebook Ads');
    const totalRow = rows.length + 2;
    const totalImpressions = rows.reduce((s, r) => s + r[2], 0);
    const totalReach = rows.reduce((s, r) => s + r[3], 0);
    const totalClicks = rows.reduce((s, r) => s + r[4], 0);
    const totalSpend = rows.reduce((s, r) => s + parseFloat(r[8].replace('$', '')), 0);
    const totalResults = rows.reduce((s, r) => s + r[9], 0);

    sheet.getRange(totalRow, 1).setValue('ИТОГО');
    sheet.getRange(totalRow, 3).setValue(totalImpressions);
    sheet.getRange(totalRow, 4).setValue(totalReach);
    sheet.getRange(totalRow, 5).setValue(totalClicks);
    sheet.getRange(totalRow, 9).setValue('$' + totalSpend.toFixed(2));
    sheet.getRange(totalRow, 10).setValue(totalResults);
    sheet.getRange(totalRow, 1, 1, 11).setFontWeight('bold');
  }
}

// ============================================================
// 8. AD PERFORMANCE — сопоставление GA4 + Facebook
// ============================================================

/**
 * Получает данные GA4 по платному трафику (paid social) по дням.
 */
function getGA4PaidSocialByDay() {
  const result = runGA4Report({
    dimensions: ['date', 'sessionSource', 'sessionMedium', 'sessionCampaignName'],
    metrics: [
      'sessions', 'totalUsers', 'engagementRate',
      'addToCarts', 'checkouts', 'ecommercePurchases', 'purchaseRevenue'
    ],
    dimensionFilter: {
      orGroup: {
        expressions: [
          {
            filter: {
              fieldName: 'sessionMedium',
              stringFilter: { value: 'paid', matchType: 'CONTAINS' }
            }
          },
          {
            filter: {
              fieldName: 'sessionMedium',
              stringFilter: { value: 'cpc', matchType: 'EXACT' }
            }
          },
          {
            filter: {
              fieldName: 'sessionMedium',
              stringFilter: { value: 'cpm', matchType: 'EXACT' }
            }
          }
        ]
      }
    },
    orderBys: [{ dimension: { dimensionName: 'date' }, desc: false }]
  });

  return extractRows(result);
}

/**
 * Сопоставляет данные Facebook Ads с GA4 paid traffic.
 */
function updateAdPerformance() {
  // GA4 paid traffic по дням
  const ga4Rows = getGA4PaidSocialByDay();

  // Агрегируем GA4 данные по дате
  const ga4ByDate = {};
  ga4Rows.forEach(r => {
    const d = r[0];
    const dateStr = d.substring(0, 4) + '-' + d.substring(4, 6) + '-' + d.substring(6, 8);
    if (!ga4ByDate[dateStr]) {
      ga4ByDate[dateStr] = {
        sessions: 0, users: 0, engagementSum: 0, engagementCount: 0,
        addToCarts: 0, checkouts: 0, purchases: 0, revenue: 0
      };
    }
    const entry = ga4ByDate[dateStr];
    entry.sessions += parseInt(r[4]);
    entry.users += parseInt(r[5]);
    entry.engagementSum += parseFloat(r[6]) * parseInt(r[4]);
    entry.engagementCount += parseInt(r[4]);
    entry.addToCarts += parseInt(r[7]);
    entry.checkouts += parseInt(r[8]);
    entry.purchases += parseInt(r[9]);
    entry.revenue += parseFloat(r[10]);
  });

  // Facebook данные по дням (агрегированные)
  let fbByDate = {};
  try {
    const fbData = getFacebookAdsData();
    fbData.forEach(row => {
      const date = row.date_start;
      if (!fbByDate[date]) {
        fbByDate[date] = { impressions: 0, clicks: 0, spend: 0, reach: 0 };
      }
      fbByDate[date].impressions += parseInt(row.impressions || 0);
      fbByDate[date].clicks += parseInt(row.clicks || 0);
      fbByDate[date].spend += parseFloat(row.spend || 0);
      fbByDate[date].reach += parseInt(row.reach || 0);
    });
  } catch (e) {
    // Facebook не настроен — покажем только GA4 данные
    Logger.log('Facebook data unavailable: ' + e.message);
  }

  // Собираем все даты
  const allDates = [...new Set([...Object.keys(ga4ByDate), ...Object.keys(fbByDate)])].sort();

  const headers = [
    'Дата',
    // Facebook
    'FB Показы', 'FB Клики', 'FB Расход',
    // GA4
    'GA4 Сессии (paid)', 'GA4 Пользователи', 'GA4 Engagement',
    'Добавл. в корзину', 'Оформления', 'Покупки', 'Доход',
    // Расчётные
    'Цена за сессию (GA4)', 'ROAS'
  ];

  const rows = allDates.map(date => {
    const fb = fbByDate[date] || { impressions: 0, clicks: 0, spend: 0, reach: 0 };
    const ga = ga4ByDate[date] || {
      sessions: 0, users: 0, engagementSum: 0, engagementCount: 0,
      addToCarts: 0, checkouts: 0, purchases: 0, revenue: 0
    };

    const engagement = ga.engagementCount > 0
      ? (ga.engagementSum / ga.engagementCount * 100).toFixed(1) + '%' : '0.0%';
    const costPerSession = fb.spend > 0 && ga.sessions > 0
      ? '$' + (fb.spend / ga.sessions).toFixed(2) : '-';
    const roas = fb.spend > 0
      ? (ga.revenue / fb.spend).toFixed(2) + 'x' : '-';

    return [
      date,
      fb.impressions,
      fb.clicks,
      '$' + fb.spend.toFixed(2),
      ga.sessions,
      ga.users,
      engagement,
      ga.addToCarts,
      ga.checkouts,
      ga.purchases,
      fmtCurrency(ga.revenue),
      costPerSession,
      roas
    ];
  });

  writeToSheet('Ad Performance', headers, rows);

  // Итоговая строка
  if (rows.length > 0) {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Ad Performance');
    const totalRow = rows.length + 2;
    const totals = rows.reduce((acc, r) => {
      acc.impressions += r[1];
      acc.clicks += r[2];
      acc.spend += parseFloat(r[3].replace('$', ''));
      acc.sessions += r[4];
      acc.users += r[5];
      acc.addToCarts += r[7];
      acc.checkouts += r[8];
      acc.purchases += r[9];
      acc.revenue += parseFloat(r[10].replace('$', ''));
      return acc;
    }, { impressions: 0, clicks: 0, spend: 0, sessions: 0, users: 0, addToCarts: 0, checkouts: 0, purchases: 0, revenue: 0 });

    const totalData = [
      'ИТОГО',
      totals.impressions,
      totals.clicks,
      '$' + totals.spend.toFixed(2),
      totals.sessions,
      totals.users,
      '',
      totals.addToCarts,
      totals.checkouts,
      totals.purchases,
      fmtCurrency(totals.revenue),
      totals.spend > 0 && totals.sessions > 0 ? '$' + (totals.spend / totals.sessions).toFixed(2) : '-',
      totals.spend > 0 ? (totals.revenue / totals.spend).toFixed(2) + 'x' : '-'
    ];

    sheet.getRange(totalRow, 1, 1, totalData.length).setValues([totalData]);
    sheet.getRange(totalRow, 1, 1, totalData.length).setFontWeight('bold');
  }
}
