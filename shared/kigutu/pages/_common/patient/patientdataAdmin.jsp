<%@page errorPage="/includes/error.jsp"%>
<%@include file="/includes/validateUser.jsp"%>
<%
    String sGender = "&nbsp;", sComment = "&nbsp;", sNativeCountry = "&nbsp;", sLanguage = "&nbsp;", sNatreg = "&nbsp;", sVip="0", sNativeTown=""
            , sCivilStatus = "&nbsp;", sTracnetID = "&nbsp;", sTreatingPhysician = "&nbsp;", sComment3="", sComment4="", sComment5="", sDeathCertificateTo="", sDeathCertificateOn="", sExport="0", sLastExport="0";

    // language
    sWebLanguage = activeUser.person.language;
    if ((activePatient.language!=null)&&(activePatient.language.trim().length()>0)) {
        sLanguage = getTran(request,"Web.language",activePatient.language,sWebLanguage);
    }

    // Gender
    if ((activePatient.gender!=null)&&(activePatient.gender.trim().length()>0)) {
        if (activePatient.gender.equalsIgnoreCase("m")){
            sGender = getTran(request,"web.occup","male",sWebLanguage);
        }
        else if (activePatient.gender.equalsIgnoreCase("f")){
            sGender = getTran(request,"web.occup","female",sWebLanguage);
        }
    }

    // civilstatus
    if ((activePatient.comment2!=null)&&(activePatient.comment2.trim().length()>0)) {
        sCivilStatus = getTran(request,"civil.status",activePatient.comment2,sWebLanguage);
    }
    // sTracnetID
    if (checkString((String)activePatient.adminextends.get("tracnetid")).length()>0) {
        sTracnetID = checkString((String)activePatient.adminextends.get("tracnetid"));
    }

    // sDeathCertificateTo
    if (checkString((String)activePatient.adminextends.get("deathcertificateto")).length()>0) {
    	sDeathCertificateTo = checkString((String)activePatient.adminextends.get("deathcertificateto"));
    }

    // sDeathCertificateOn
    if (checkString((String)activePatient.adminextends.get("deathcertificateon")).length()>0) {
    	sDeathCertificateOn = checkString((String)activePatient.adminextends.get("deathcertificateon"));
    }

    // sTreatingPhysician
    if (checkString(activePatient.comment1).length()>0) {
        sTreatingPhysician = activePatient.comment1;
    }

    // comment
    if ((activePatient.comment!=null)&&(activePatient.comment.trim().length()>0)) {
        sComment = (activePatient.comment);
    }

    // comment3
    if ((activePatient.comment3!=null)&&(activePatient.comment3.trim().length()>0)) {
        sComment3 = (activePatient.comment3);
    }

    // comment4
    if ((activePatient.comment4!=null)&&(activePatient.comment4.trim().length()>0)) {
        sComment4 = (activePatient.comment4);
    }
	
    // comment5
    if ((activePatient.comment5!=null)&&(activePatient.comment5.trim().length()>0)) {
        sComment5 = (activePatient.comment5);
    }

    // nativeCountry
    if ((activePatient.nativeCountry!=null)&&(activePatient.nativeCountry.trim().length()>0)) {
        sNativeCountry = getTran(request,"Country",activePatient.nativeCountry,sWebLanguage);
    }

    // nativeCountry
    if ((activePatient.nativeTown!=null)&&(activePatient.nativeTown.trim().length()>0)) {
        sNativeTown = getTran(request,"NativeTown",activePatient.nativeTown,sWebLanguage);
    }

    // nat reg
    if (checkString(activePatient.getID("natreg")).length()>0) {
        sNatreg = activePatient.getID("natreg");
    }

    // VIP
    if (be.openclinic.core.db.Config.getConfigInt("enableVip",0)==1 && checkString((String)activePatient.adminextends.get("vip")).length()>0) {
        sVip = (String)activePatient.adminextends.get("vip");
        if(sVip==null || sVip.length()==0){
        	sVip="0";
        }
    }

    // ExportRequest
    if (be.openclinic.core.db.Config.getConfigInt("enableDatacenterPatientExport",0)==1 && activePatient.hasPendingExportRequest()) {
		sExport="1";
    }
%>
<%-- MAIN TABLE ----------------------------------------------------------------------------------%>
<table width='100%' cellspacing="1" class="list" style="border-top:none;">
    <%=(
         (
            be.openclinic.core.db.Config.getConfigInt("showAdminNativeCountry",1)==0?"":
            setRow(request,"Web","nativecountry",sNativeCountry,sWebLanguage)
         )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminLanguage",1)==0?"":
            setRow(request,"Web","Language",sLanguage,sWebLanguage)
        )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminGender",1)==0?"":
            setRow(request,"Web","Gender",sGender,sWebLanguage)
        )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminComment2",1)==0?"":
            setRow(request,"Web","civilstatus",sCivilStatus,sWebLanguage)
        )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminNatReg",1)==0?"":
            setRow(request,"Web","natreg",sNatreg,sWebLanguage)
        )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminComment1",1)==0?"":
            setRow(request,"Web","treating-physician",sTreatingPhysician,sWebLanguage)
        )
        +(
                be.openclinic.core.db.Config.getConfigInt("showAdminComment3",1)==0?"":
                setRow(request,"Web","comment3",sComment3,sWebLanguage)
            )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminComment",1)==0?"":
            setRow(request,"Web","comment",sComment,sWebLanguage)
        )
        +(
                be.openclinic.core.db.Config.getConfigInt("showAdminComment4",1)==0?"":
                setRow(request,"Web","comment4",sComment4,sWebLanguage)
            )
        +(
            be.openclinic.core.db.Config.getConfigInt("showAdminComment5",1)==0?"":
            setRow(request,"Web","comment5",getTranNoLink("comment5.options",sComment5,sWebLanguage),sWebLanguage)
			)
        +(
                be.openclinic.core.db.Config.getConfigInt("showAdminTracnetID",1)==0?"":
                setRow(request,"Web","tracnetid",sTracnetID,sWebLanguage)
            )
        +(be.openclinic.core.db.Config.getConfigInt("enableVip",0)==1?setRow(request,"Web","vip",getTran(request,"vipstatus",sVip,sWebLanguage),sWebLanguage):"")
        +(be.openclinic.core.db.Config.getConfigInt("enableDatacenterPatientExport",0)==1?setRow(request,"Web","datacenterpatientexport",getTran(request,"datacenterpatientexport",sExport,sWebLanguage),sWebLanguage):"")
        +(be.openclinic.core.db.Config.getConfigInt("enableDatacenterPatientExport",0)==1?setRow(request,"Web","lastdatacenterpatientexport",activePatient.getLastSentExportRequest(),sWebLanguage):"")
        +(activePatient.isDead()!=null?setRow(request,"Web","deathcertificateon",sDeathCertificateOn,sWebLanguage)+setRow(request,"Web","deathcertificateto",sDeathCertificateTo,sWebLanguage):"")
        )
    %>
    <tr height='1'><td width='<%=sTDAdminWidth%>'/></tr>
</table>
<%
    String sShowButton = checkString(request.getParameter("ShowButton"));
    if (!sShowButton.equals("false")){
%>
<%-- BUTTONS -------------------------------------------------------------------------------------%>
<%=ScreenHelper.alignButtonsStart()%>
    <%
        if (activeUser.getAccessRight("patient.administration.edit")){
        %>
            <input type="button" class="button" onclick="window.location.href='<c:url value="/patientedit.do"/>?Tab=Admin&ts=<%=getTs()%>'" value="<%=getTranNoLink("Web","edit",sWebLanguage)%>"/>
        <%
        }
    %>
<%=ScreenHelper.alignButtonsStop()%>
<%
    }
%>