function loadVIN(twc, vin) {
  window.open("/vehicleDetails/" + document.getElementById(twc+"_"+vin+"VIN").innerHTML, '_blank');
}

