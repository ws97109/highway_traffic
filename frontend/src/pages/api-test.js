// 這是一個臨時診斷頁面，用來檢查 Google Maps API 設定
export default function ApiTest() {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  
  return (
    <div style={{ padding: '20px' }}>
      <h1>API 金鑰檢查</h1>
      <p>API 金鑰狀態: {apiKey ? '已設定' : '未設定'}</p>
      <p>API 金鑰長度: {apiKey ? apiKey.length : 0}</p>
      <p>API 金鑰前4碼: {apiKey ? apiKey.substring(0, 4) : 'N/A'}</p>
      
      <h2>測試 Google Maps API 載入</h2>
      <div id="map-test" style={{ height: '300px', width: '100%', backgroundColor: '#f0f0f0' }}>
        地圖載入區域
      </div>
      
      <script
        src={`https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=initMap`}
        async
        defer
        onLoad={() => console.log('Google Maps script loaded')}
        onError={() => console.error('Google Maps script failed to load')}
      />
      
      <script
        dangerouslySetInnerHTML={{
          __html: `
            function initMap() {
              console.log('Google Maps initialized successfully');
              const map = new google.maps.Map(document.getElementById('map-test'), {
                center: { lat: 25.033, lng: 121.5654 },
                zoom: 10
              });
            }
            
            window.initMap = initMap;
          `
        }}
      />
    </div>
  );
}
