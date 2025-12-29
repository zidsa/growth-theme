/**
 * Countries Data with Phone Validation
 *
 * Comprehensive list of countries with dial codes, names, and phone validation rules.
 * phoneLengths: Array of valid national number lengths (without country code).
 *
 * Data sourced from ITU-T E.164 and libphonenumber metadata.
 */
const CountriesData = [
  // Gulf Cooperation Council (GCC) - Priority
  { code: "SA", dialCode: "+966", name: "Saudi Arabia", nameAr: "السعودية", phoneLengths: [9] },
  { code: "AE", dialCode: "+971", name: "United Arab Emirates", nameAr: "الإمارات", phoneLengths: [9] },
  { code: "KW", dialCode: "+965", name: "Kuwait", nameAr: "الكويت", phoneLengths: [8] },
  { code: "BH", dialCode: "+973", name: "Bahrain", nameAr: "البحرين", phoneLengths: [8] },
  { code: "QA", dialCode: "+974", name: "Qatar", nameAr: "قطر", phoneLengths: [8] },
  { code: "OM", dialCode: "+968", name: "Oman", nameAr: "عُمان", phoneLengths: [8] },

  // Other Arab Countries
  { code: "EG", dialCode: "+20", name: "Egypt", nameAr: "مصر", phoneLengths: [10] },
  { code: "JO", dialCode: "+962", name: "Jordan", nameAr: "الأردن", phoneLengths: [9] },
  { code: "LB", dialCode: "+961", name: "Lebanon", nameAr: "لبنان", phoneLengths: [7, 8] },
  { code: "IQ", dialCode: "+964", name: "Iraq", nameAr: "العراق", phoneLengths: [10] },
  { code: "SY", dialCode: "+963", name: "Syria", nameAr: "سوريا", phoneLengths: [9] },
  { code: "YE", dialCode: "+967", name: "Yemen", nameAr: "اليمن", phoneLengths: [9] },
  { code: "PS", dialCode: "+970", name: "Palestine", nameAr: "فلسطين", phoneLengths: [9] },
  { code: "SD", dialCode: "+249", name: "Sudan", nameAr: "السودان", phoneLengths: [9] },
  { code: "LY", dialCode: "+218", name: "Libya", nameAr: "ليبيا", phoneLengths: [9] },
  { code: "TN", dialCode: "+216", name: "Tunisia", nameAr: "تونس", phoneLengths: [8] },
  { code: "DZ", dialCode: "+213", name: "Algeria", nameAr: "الجزائر", phoneLengths: [9] },
  { code: "MA", dialCode: "+212", name: "Morocco", nameAr: "المغرب", phoneLengths: [9] },
  { code: "MR", dialCode: "+222", name: "Mauritania", nameAr: "موريتانيا", phoneLengths: [8] },
  { code: "SO", dialCode: "+252", name: "Somalia", nameAr: "الصومال", phoneLengths: [8, 9] },
  { code: "DJ", dialCode: "+253", name: "Djibouti", nameAr: "جيبوتي", phoneLengths: [8] },
  { code: "KM", dialCode: "+269", name: "Comoros", nameAr: "جزر القمر", phoneLengths: [7] },

  // Rest of the World (Alphabetically by name)
  { code: "AF", dialCode: "+93", name: "Afghanistan", nameAr: "أفغانستان", phoneLengths: [9] },
  { code: "AL", dialCode: "+355", name: "Albania", nameAr: "ألبانيا", phoneLengths: [9] },
  { code: "AD", dialCode: "+376", name: "Andorra", nameAr: "أندورا", phoneLengths: [6, 8, 9] },
  { code: "AO", dialCode: "+244", name: "Angola", nameAr: "أنغولا", phoneLengths: [9] },
  { code: "AG", dialCode: "+1268", name: "Antigua and Barbuda", nameAr: "أنتيغوا وبربودا", phoneLengths: [7] },
  { code: "AR", dialCode: "+54", name: "Argentina", nameAr: "الأرجنتين", phoneLengths: [10, 11] },
  { code: "AM", dialCode: "+374", name: "Armenia", nameAr: "أرمينيا", phoneLengths: [8] },
  { code: "AU", dialCode: "+61", name: "Australia", nameAr: "أستراليا", phoneLengths: [9] },
  { code: "AT", dialCode: "+43", name: "Austria", nameAr: "النمسا", phoneLengths: [10, 11, 12, 13] },
  { code: "AZ", dialCode: "+994", name: "Azerbaijan", nameAr: "أذربيجان", phoneLengths: [9] },
  { code: "BS", dialCode: "+1242", name: "Bahamas", nameAr: "الباهاما", phoneLengths: [7] },
  { code: "BD", dialCode: "+880", name: "Bangladesh", nameAr: "بنغلاديش", phoneLengths: [10] },
  { code: "BB", dialCode: "+1246", name: "Barbados", nameAr: "بربادوس", phoneLengths: [7] },
  { code: "BY", dialCode: "+375", name: "Belarus", nameAr: "بيلاروسيا", phoneLengths: [9] },
  { code: "BE", dialCode: "+32", name: "Belgium", nameAr: "بلجيكا", phoneLengths: [9] },
  { code: "BZ", dialCode: "+501", name: "Belize", nameAr: "بليز", phoneLengths: [7] },
  { code: "BJ", dialCode: "+229", name: "Benin", nameAr: "بنين", phoneLengths: [8] },
  { code: "BT", dialCode: "+975", name: "Bhutan", nameAr: "بوتان", phoneLengths: [8] },
  { code: "BO", dialCode: "+591", name: "Bolivia", nameAr: "بوليفيا", phoneLengths: [8] },
  { code: "BA", dialCode: "+387", name: "Bosnia and Herzegovina", nameAr: "البوسنة والهرسك", phoneLengths: [8, 9] },
  { code: "BW", dialCode: "+267", name: "Botswana", nameAr: "بوتسوانا", phoneLengths: [8] },
  { code: "BR", dialCode: "+55", name: "Brazil", nameAr: "البرازيل", phoneLengths: [10, 11] },
  { code: "BN", dialCode: "+673", name: "Brunei", nameAr: "بروناي", phoneLengths: [7] },
  { code: "BG", dialCode: "+359", name: "Bulgaria", nameAr: "بلغاريا", phoneLengths: [9] },
  { code: "BF", dialCode: "+226", name: "Burkina Faso", nameAr: "بوركينا فاسو", phoneLengths: [8] },
  { code: "BI", dialCode: "+257", name: "Burundi", nameAr: "بوروندي", phoneLengths: [8] },
  { code: "KH", dialCode: "+855", name: "Cambodia", nameAr: "كمبوديا", phoneLengths: [8, 9] },
  { code: "CM", dialCode: "+237", name: "Cameroon", nameAr: "الكاميرون", phoneLengths: [9] },
  { code: "CA", dialCode: "+1", name: "Canada", nameAr: "كندا", phoneLengths: [10] },
  { code: "CV", dialCode: "+238", name: "Cape Verde", nameAr: "الرأس الأخضر", phoneLengths: [7] },
  {
    code: "CF",
    dialCode: "+236",
    name: "Central African Republic",
    nameAr: "جمهورية أفريقيا الوسطى",
    phoneLengths: [8]
  },
  { code: "TD", dialCode: "+235", name: "Chad", nameAr: "تشاد", phoneLengths: [8] },
  { code: "CL", dialCode: "+56", name: "Chile", nameAr: "تشيلي", phoneLengths: [9] },
  { code: "CN", dialCode: "+86", name: "China", nameAr: "الصين", phoneLengths: [11] },
  { code: "CO", dialCode: "+57", name: "Colombia", nameAr: "كولومبيا", phoneLengths: [10] },
  { code: "CG", dialCode: "+242", name: "Congo", nameAr: "الكونغو", phoneLengths: [9] },
  { code: "CD", dialCode: "+243", name: "Congo (DRC)", nameAr: "الكونغو الديمقراطية", phoneLengths: [9] },
  { code: "CR", dialCode: "+506", name: "Costa Rica", nameAr: "كوستاريكا", phoneLengths: [8] },
  { code: "CI", dialCode: "+225", name: "Côte d'Ivoire", nameAr: "ساحل العاج", phoneLengths: [10] },
  { code: "HR", dialCode: "+385", name: "Croatia", nameAr: "كرواتيا", phoneLengths: [9] },
  { code: "CU", dialCode: "+53", name: "Cuba", nameAr: "كوبا", phoneLengths: [8] },
  { code: "CY", dialCode: "+357", name: "Cyprus", nameAr: "قبرص", phoneLengths: [8] },
  { code: "CZ", dialCode: "+420", name: "Czech Republic", nameAr: "التشيك", phoneLengths: [9] },
  { code: "DK", dialCode: "+45", name: "Denmark", nameAr: "الدنمارك", phoneLengths: [8] },
  { code: "DM", dialCode: "+1767", name: "Dominica", nameAr: "دومينيكا", phoneLengths: [7] },
  { code: "DO", dialCode: "+1809", name: "Dominican Republic", nameAr: "جمهورية الدومينيكان", phoneLengths: [10] },
  { code: "EC", dialCode: "+593", name: "Ecuador", nameAr: "الإكوادور", phoneLengths: [9] },
  { code: "SV", dialCode: "+503", name: "El Salvador", nameAr: "السلفادور", phoneLengths: [8] },
  { code: "GQ", dialCode: "+240", name: "Equatorial Guinea", nameAr: "غينيا الاستوائية", phoneLengths: [9] },
  { code: "ER", dialCode: "+291", name: "Eritrea", nameAr: "إريتريا", phoneLengths: [7] },
  { code: "EE", dialCode: "+372", name: "Estonia", nameAr: "إستونيا", phoneLengths: [7, 8] },
  { code: "SZ", dialCode: "+268", name: "Eswatini", nameAr: "إسواتيني", phoneLengths: [8] },
  { code: "ET", dialCode: "+251", name: "Ethiopia", nameAr: "إثيوبيا", phoneLengths: [9] },
  { code: "FJ", dialCode: "+679", name: "Fiji", nameAr: "فيجي", phoneLengths: [7] },
  { code: "FI", dialCode: "+358", name: "Finland", nameAr: "فنلندا", phoneLengths: [9, 10] },
  { code: "FR", dialCode: "+33", name: "France", nameAr: "فرنسا", phoneLengths: [9] },
  { code: "GA", dialCode: "+241", name: "Gabon", nameAr: "الغابون", phoneLengths: [8] },
  { code: "GM", dialCode: "+220", name: "Gambia", nameAr: "غامبيا", phoneLengths: [7] },
  { code: "GE", dialCode: "+995", name: "Georgia", nameAr: "جورجيا", phoneLengths: [9] },
  { code: "DE", dialCode: "+49", name: "Germany", nameAr: "ألمانيا", phoneLengths: [10, 11] },
  { code: "GH", dialCode: "+233", name: "Ghana", nameAr: "غانا", phoneLengths: [9] },
  { code: "GR", dialCode: "+30", name: "Greece", nameAr: "اليونان", phoneLengths: [10] },
  { code: "GD", dialCode: "+1473", name: "Grenada", nameAr: "غرينادا", phoneLengths: [7] },
  { code: "GT", dialCode: "+502", name: "Guatemala", nameAr: "غواتيمالا", phoneLengths: [8] },
  { code: "GN", dialCode: "+224", name: "Guinea", nameAr: "غينيا", phoneLengths: [9] },
  { code: "GW", dialCode: "+245", name: "Guinea-Bissau", nameAr: "غينيا بيساو", phoneLengths: [9] },
  { code: "GY", dialCode: "+592", name: "Guyana", nameAr: "غيانا", phoneLengths: [7] },
  { code: "HT", dialCode: "+509", name: "Haiti", nameAr: "هايتي", phoneLengths: [8] },
  { code: "HN", dialCode: "+504", name: "Honduras", nameAr: "هندوراس", phoneLengths: [8] },
  { code: "HK", dialCode: "+852", name: "Hong Kong", nameAr: "هونغ كونغ", phoneLengths: [8] },
  { code: "HU", dialCode: "+36", name: "Hungary", nameAr: "المجر", phoneLengths: [9] },
  { code: "IS", dialCode: "+354", name: "Iceland", nameAr: "آيسلندا", phoneLengths: [7] },
  { code: "IN", dialCode: "+91", name: "India", nameAr: "الهند", phoneLengths: [10] },
  { code: "ID", dialCode: "+62", name: "Indonesia", nameAr: "إندونيسيا", phoneLengths: [9, 10, 11, 12] },
  { code: "IR", dialCode: "+98", name: "Iran", nameAr: "إيران", phoneLengths: [10] },
  { code: "IE", dialCode: "+353", name: "Ireland", nameAr: "أيرلندا", phoneLengths: [9] },
  { code: "IL", dialCode: "+972", name: "Israel", nameAr: "إسرائيل", phoneLengths: [9] },
  { code: "IT", dialCode: "+39", name: "Italy", nameAr: "إيطاليا", phoneLengths: [10] },
  { code: "JM", dialCode: "+1876", name: "Jamaica", nameAr: "جامايكا", phoneLengths: [7] },
  { code: "JP", dialCode: "+81", name: "Japan", nameAr: "اليابان", phoneLengths: [10] },
  { code: "KZ", dialCode: "+7", name: "Kazakhstan", nameAr: "كازاخستان", phoneLengths: [10] },
  { code: "KE", dialCode: "+254", name: "Kenya", nameAr: "كينيا", phoneLengths: [9] },
  { code: "KI", dialCode: "+686", name: "Kiribati", nameAr: "كيريباتي", phoneLengths: [8] },
  { code: "KP", dialCode: "+850", name: "North Korea", nameAr: "كوريا الشمالية", phoneLengths: [10] },
  { code: "KR", dialCode: "+82", name: "South Korea", nameAr: "كوريا الجنوبية", phoneLengths: [9, 10] },
  { code: "XK", dialCode: "+383", name: "Kosovo", nameAr: "كوسوفو", phoneLengths: [8] },
  { code: "KG", dialCode: "+996", name: "Kyrgyzstan", nameAr: "قيرغيزستان", phoneLengths: [9] },
  { code: "LA", dialCode: "+856", name: "Laos", nameAr: "لاوس", phoneLengths: [10] },
  { code: "LV", dialCode: "+371", name: "Latvia", nameAr: "لاتفيا", phoneLengths: [8] },
  { code: "LS", dialCode: "+266", name: "Lesotho", nameAr: "ليسوتو", phoneLengths: [8] },
  { code: "LR", dialCode: "+231", name: "Liberia", nameAr: "ليبيريا", phoneLengths: [8, 9] },
  { code: "LI", dialCode: "+423", name: "Liechtenstein", nameAr: "ليختنشتاين", phoneLengths: [7] },
  { code: "LT", dialCode: "+370", name: "Lithuania", nameAr: "ليتوانيا", phoneLengths: [8] },
  { code: "LU", dialCode: "+352", name: "Luxembourg", nameAr: "لوكسمبورغ", phoneLengths: [9] },
  { code: "MO", dialCode: "+853", name: "Macau", nameAr: "ماكاو", phoneLengths: [8] },
  { code: "MG", dialCode: "+261", name: "Madagascar", nameAr: "مدغشقر", phoneLengths: [9] },
  { code: "MW", dialCode: "+265", name: "Malawi", nameAr: "مالاوي", phoneLengths: [9] },
  { code: "MY", dialCode: "+60", name: "Malaysia", nameAr: "ماليزيا", phoneLengths: [9, 10] },
  { code: "MV", dialCode: "+960", name: "Maldives", nameAr: "المالديف", phoneLengths: [7] },
  { code: "ML", dialCode: "+223", name: "Mali", nameAr: "مالي", phoneLengths: [8] },
  { code: "MT", dialCode: "+356", name: "Malta", nameAr: "مالطا", phoneLengths: [8] },
  { code: "MH", dialCode: "+692", name: "Marshall Islands", nameAr: "جزر مارشال", phoneLengths: [7] },
  { code: "MX", dialCode: "+52", name: "Mexico", nameAr: "المكسيك", phoneLengths: [10] },
  { code: "FM", dialCode: "+691", name: "Micronesia", nameAr: "ميكرونيزيا", phoneLengths: [7] },
  { code: "MD", dialCode: "+373", name: "Moldova", nameAr: "مولدوفا", phoneLengths: [8] },
  { code: "MC", dialCode: "+377", name: "Monaco", nameAr: "موناكو", phoneLengths: [8, 9] },
  { code: "MN", dialCode: "+976", name: "Mongolia", nameAr: "منغوليا", phoneLengths: [8] },
  { code: "ME", dialCode: "+382", name: "Montenegro", nameAr: "الجبل الأسود", phoneLengths: [8] },
  { code: "MZ", dialCode: "+258", name: "Mozambique", nameAr: "موزمبيق", phoneLengths: [9] },
  { code: "MM", dialCode: "+95", name: "Myanmar", nameAr: "ميانمار", phoneLengths: [8, 9, 10] },
  { code: "NA", dialCode: "+264", name: "Namibia", nameAr: "ناميبيا", phoneLengths: [9] },
  { code: "NR", dialCode: "+674", name: "Nauru", nameAr: "ناورو", phoneLengths: [7] },
  { code: "NP", dialCode: "+977", name: "Nepal", nameAr: "نيبال", phoneLengths: [10] },
  { code: "NL", dialCode: "+31", name: "Netherlands", nameAr: "هولندا", phoneLengths: [9] },
  { code: "NZ", dialCode: "+64", name: "New Zealand", nameAr: "نيوزيلندا", phoneLengths: [9, 10] },
  { code: "NI", dialCode: "+505", name: "Nicaragua", nameAr: "نيكاراغوا", phoneLengths: [8] },
  { code: "NE", dialCode: "+227", name: "Niger", nameAr: "النيجر", phoneLengths: [8] },
  { code: "NG", dialCode: "+234", name: "Nigeria", nameAr: "نيجيريا", phoneLengths: [10] },
  { code: "MK", dialCode: "+389", name: "North Macedonia", nameAr: "مقدونيا الشمالية", phoneLengths: [8] },
  { code: "NO", dialCode: "+47", name: "Norway", nameAr: "النرويج", phoneLengths: [8] },
  { code: "PK", dialCode: "+92", name: "Pakistan", nameAr: "باكستان", phoneLengths: [10] },
  { code: "PW", dialCode: "+680", name: "Palau", nameAr: "بالاو", phoneLengths: [7] },
  { code: "PA", dialCode: "+507", name: "Panama", nameAr: "بنما", phoneLengths: [8] },
  { code: "PG", dialCode: "+675", name: "Papua New Guinea", nameAr: "بابوا غينيا الجديدة", phoneLengths: [8] },
  { code: "PY", dialCode: "+595", name: "Paraguay", nameAr: "باراغواي", phoneLengths: [9] },
  { code: "PE", dialCode: "+51", name: "Peru", nameAr: "بيرو", phoneLengths: [9] },
  { code: "PH", dialCode: "+63", name: "Philippines", nameAr: "الفلبين", phoneLengths: [10] },
  { code: "PL", dialCode: "+48", name: "Poland", nameAr: "بولندا", phoneLengths: [9] },
  { code: "PT", dialCode: "+351", name: "Portugal", nameAr: "البرتغال", phoneLengths: [9] },
  { code: "PR", dialCode: "+1787", name: "Puerto Rico", nameAr: "بورتوريكو", phoneLengths: [10] },
  { code: "RO", dialCode: "+40", name: "Romania", nameAr: "رومانيا", phoneLengths: [9] },
  { code: "RU", dialCode: "+7", name: "Russia", nameAr: "روسيا", phoneLengths: [10] },
  { code: "RW", dialCode: "+250", name: "Rwanda", nameAr: "رواندا", phoneLengths: [9] },
  { code: "KN", dialCode: "+1869", name: "Saint Kitts and Nevis", nameAr: "سانت كيتس ونيفيس", phoneLengths: [7] },
  { code: "LC", dialCode: "+1758", name: "Saint Lucia", nameAr: "سانت لوسيا", phoneLengths: [7] },
  {
    code: "VC",
    dialCode: "+1784",
    name: "Saint Vincent and the Grenadines",
    nameAr: "سانت فينسنت والغرينادين",
    phoneLengths: [7]
  },
  { code: "WS", dialCode: "+685", name: "Samoa", nameAr: "ساموا", phoneLengths: [7] },
  { code: "SM", dialCode: "+378", name: "San Marino", nameAr: "سان مارينو", phoneLengths: [10] },
  { code: "ST", dialCode: "+239", name: "São Tomé and Príncipe", nameAr: "ساو تومي وبرينسيب", phoneLengths: [7] },
  { code: "SN", dialCode: "+221", name: "Senegal", nameAr: "السنغال", phoneLengths: [9] },
  { code: "RS", dialCode: "+381", name: "Serbia", nameAr: "صربيا", phoneLengths: [9] },
  { code: "SC", dialCode: "+248", name: "Seychelles", nameAr: "سيشل", phoneLengths: [7] },
  { code: "SL", dialCode: "+232", name: "Sierra Leone", nameAr: "سيراليون", phoneLengths: [8] },
  { code: "SG", dialCode: "+65", name: "Singapore", nameAr: "سنغافورة", phoneLengths: [8] },
  { code: "SK", dialCode: "+421", name: "Slovakia", nameAr: "سلوفاكيا", phoneLengths: [9] },
  { code: "SI", dialCode: "+386", name: "Slovenia", nameAr: "سلوفينيا", phoneLengths: [8] },
  { code: "SB", dialCode: "+677", name: "Solomon Islands", nameAr: "جزر سليمان", phoneLengths: [7] },
  { code: "ZA", dialCode: "+27", name: "South Africa", nameAr: "جنوب أفريقيا", phoneLengths: [9] },
  { code: "SS", dialCode: "+211", name: "South Sudan", nameAr: "جنوب السودان", phoneLengths: [9] },
  { code: "ES", dialCode: "+34", name: "Spain", nameAr: "إسبانيا", phoneLengths: [9] },
  { code: "LK", dialCode: "+94", name: "Sri Lanka", nameAr: "سريلانكا", phoneLengths: [9] },
  { code: "SR", dialCode: "+597", name: "Suriname", nameAr: "سورينام", phoneLengths: [7] },
  { code: "SE", dialCode: "+46", name: "Sweden", nameAr: "السويد", phoneLengths: [9] },
  { code: "CH", dialCode: "+41", name: "Switzerland", nameAr: "سويسرا", phoneLengths: [9] },
  { code: "TW", dialCode: "+886", name: "Taiwan", nameAr: "تايوان", phoneLengths: [9] },
  { code: "TJ", dialCode: "+992", name: "Tajikistan", nameAr: "طاجيكستان", phoneLengths: [9] },
  { code: "TZ", dialCode: "+255", name: "Tanzania", nameAr: "تنزانيا", phoneLengths: [9] },
  { code: "TH", dialCode: "+66", name: "Thailand", nameAr: "تايلاند", phoneLengths: [9] },
  { code: "TL", dialCode: "+670", name: "Timor-Leste", nameAr: "تيمور الشرقية", phoneLengths: [8] },
  { code: "TG", dialCode: "+228", name: "Togo", nameAr: "توغو", phoneLengths: [8] },
  { code: "TO", dialCode: "+676", name: "Tonga", nameAr: "تونغا", phoneLengths: [7] },
  { code: "TT", dialCode: "+1868", name: "Trinidad and Tobago", nameAr: "ترينيداد وتوباغو", phoneLengths: [7] },
  { code: "TR", dialCode: "+90", name: "Turkey", nameAr: "تركيا", phoneLengths: [10] },
  { code: "TM", dialCode: "+993", name: "Turkmenistan", nameAr: "تركمانستان", phoneLengths: [8] },
  { code: "TV", dialCode: "+688", name: "Tuvalu", nameAr: "توفالو", phoneLengths: [6] },
  { code: "UG", dialCode: "+256", name: "Uganda", nameAr: "أوغندا", phoneLengths: [9] },
  { code: "UA", dialCode: "+380", name: "Ukraine", nameAr: "أوكرانيا", phoneLengths: [9] },
  { code: "GB", dialCode: "+44", name: "United Kingdom", nameAr: "المملكة المتحدة", phoneLengths: [10] },
  { code: "US", dialCode: "+1", name: "United States", nameAr: "الولايات المتحدة", phoneLengths: [10] },
  { code: "UY", dialCode: "+598", name: "Uruguay", nameAr: "أوروغواي", phoneLengths: [8] },
  { code: "UZ", dialCode: "+998", name: "Uzbekistan", nameAr: "أوزبكستان", phoneLengths: [9] },
  { code: "VU", dialCode: "+678", name: "Vanuatu", nameAr: "فانواتو", phoneLengths: [7] },
  { code: "VA", dialCode: "+379", name: "Vatican City", nameAr: "الفاتيكان", phoneLengths: [10] },
  { code: "VE", dialCode: "+58", name: "Venezuela", nameAr: "فنزويلا", phoneLengths: [10] },
  { code: "VN", dialCode: "+84", name: "Vietnam", nameAr: "فيتنام", phoneLengths: [9, 10] },
  { code: "ZM", dialCode: "+260", name: "Zambia", nameAr: "زامبيا", phoneLengths: [9] },
  { code: "ZW", dialCode: "+263", name: "Zimbabwe", nameAr: "زيمبابوي", phoneLengths: [9] }
];

/**
 * Helper methods
 */
function getGCCCountries() {
  return CountriesData.slice(0, 6);
}

function getArabCountries() {
  return CountriesData.slice(0, 22);
}

function getByDialCode(dialCode) {
  return CountriesData.find((c) => c.dialCode === dialCode);
}

function getByCode(code) {
  return CountriesData.find((c) => c.code === code);
}

/**
 * Phone Number Validation
 *
 * Validates phone number length for a given country.
 * Returns: undefined (valid), 'TOO_SHORT', 'TOO_LONG', or 'INVALID_LENGTH'
 */
function validatePhoneLength(phoneNumber, countryCode) {
  const country = getByCode(countryCode) || getByDialCode(countryCode);
  if (!country) return "INVALID_COUNTRY";

  // Clean phone number - digits only
  const digits = phoneNumber.replace(/\D/g, "");
  const length = digits.length;

  if (!country.phoneLengths || country.phoneLengths.length === 0) {
    // No length data - accept 7-15 digits (ITU-T E.164 range)
    if (length < 7) return "TOO_SHORT";
    if (length > 15) return "TOO_LONG";
    return undefined;
  }

  const minLength = Math.min(...country.phoneLengths);
  const maxLength = Math.max(...country.phoneLengths);

  if (length < minLength) return "TOO_SHORT";
  if (length > maxLength) return "TOO_LONG";

  // Check if length matches any valid length
  if (!country.phoneLengths.includes(length)) {
    return "INVALID_LENGTH";
  }

  return undefined; // Valid
}

/**
 * Check if phone number is possible (valid length)
 */
function isPossiblePhoneNumber(phoneNumber, countryCode) {
  return validatePhoneLength(phoneNumber, countryCode) === undefined;
}

// Attach methods to array for backward compatibility
CountriesData.getGCCCountries = getGCCCountries;
CountriesData.getArabCountries = getArabCountries;
CountriesData.getByDialCode = getByDialCode;
CountriesData.getByCode = getByCode;
CountriesData.validatePhoneLength = validatePhoneLength;
CountriesData.isPossiblePhoneNumber = isPossiblePhoneNumber;

// Expose globally for backward compatibility
window.CountriesData = CountriesData;

export {
  CountriesData,
  getGCCCountries,
  getArabCountries,
  getByDialCode,
  getByCode,
  validatePhoneLength,
  isPossiblePhoneNumber
};
export default CountriesData;
